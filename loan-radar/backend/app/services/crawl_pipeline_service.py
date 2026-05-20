from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.collectors import CollectorFactory
from app.collectors.base import CollectionAuthError, CollectionNoDataError, CollectionRequestError
from app.collectors.config import CollectorConfig
from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.note import Note, NoteComment
from app.models.post import Post
from app.services.competitor_discovery_service import CompetitorDiscoveryService
from app.services.crawl_task_service import (
    create_running_crawl_task,
    mark_crawl_task_failed,
    mark_crawl_task_success,
    update_crawl_task_progress,
)
from app.services.cookie_resolution_service import inject_cookies_into_config
from app.services.dedup_service import batch_dedup_comments, batch_dedup_posts, check_lead_duplicate, compute_content_hash
from app.services.failure_classifier import FailureType, classify_failure_type
from app.services.lead_scoring_service import LeadScoringService
from app.services.notification_service import _create as _notify


def _sanitize_error_message(error: Exception | str) -> str:
    msg = str(error)
    msg = re.sub(r'cookie["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'cookie=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'(api[_-]?)?key["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'key=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'token["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'token=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'password=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'authorization["\']?\s*[:=]\s*["\']?[^"\';\s]+', 'Authorization=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'[?&](key|token|auth|api_key|apikey)=[^&\s]+', '&key=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'sessionid=[^&;\s]+', 'sessionid=***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'(mysql|postgres|mongodb|redis)://[^\s"\']+', r'\1://***', msg, flags=re.IGNORECASE)
    msg = re.sub(r'Traceback \(most recent call last\):.*', '[internal error details omitted]', msg, flags=re.DOTALL)
    msg = re.sub(r'File "[^"]+", line \d+.*', '[stack trace omitted]', msg, flags=re.IGNORECASE)
    return msg


def _should_use_media_crawler(source: MonitorSource) -> bool:
    config = source.config if isinstance(source.config, dict) else {}
    collector_type = str(config.get("collector_type") or "").strip().lower()
    return collector_type == "media_crawler"


def _get_time_range_cutoff(source: MonitorSource) -> datetime | None:
    config = CollectorConfig.parse(source.config)
    days = config.get_time_range_days()
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


def _filter_posts_by_time_range(
    posts: list,
    cutoff: datetime | None,
) -> list:
    if cutoff is None:
        return posts
    return [p for p in posts if p.publish_time is not None and p.publish_time >= cutoff]


def _filter_comments_by_time_range(
    comments: list,
    cutoff: datetime | None,
) -> list:
    if cutoff is None:
        return comments
    return [c for c in comments if c.publish_time is not None and c.publish_time >= cutoff]


def _get_effective_max_posts(source: MonitorSource) -> int:
    config = CollectorConfig.parse(source.config)
    return config.get_effective_max_posts()


def _dual_write_note(db: Session, post: Post) -> None:
    from sqlalchemy import select as sa_select

    existing = db.scalar(
        sa_select(Note).where(
            Note.platform == post.platform,
            Note.note_id == post.post_id,
        )
    )
    if existing is not None:
        return

    raw_json = post.raw_data if isinstance(post.raw_data, dict) else {}
    if not raw_json:
        raw_json = {
            "liked_count": post.like_count,
            "collected_count": post.collect_count,
            "comment_count": post.comment_count,
        }

    note = Note(
        user_id=None,
        platform_account_id=None,
        platform=post.platform,
        note_id=post.post_id,
        title=post.title or "",
        content=post.content or "",
        author_name=post.author_name or "",
        raw_json=raw_json,
    )
    db.add(note)
    db.flush()

    post_comments = db.scalars(
        sa_select(Comment).where(
            Comment.platform == post.platform,
            Comment.post_id == post.post_id,
        )
    ).all()

    for comment in post_comments:
        existing_nc = db.scalar(
            sa_select(NoteComment).where(
                NoteComment.note_id == note.id,
                NoteComment.comment_id == comment.comment_id,
            )
        )
        if existing_nc is not None:
            continue
        nc = NoteComment(
            note_id=note.id,
            comment_id=comment.comment_id,
            user_name=comment.user_name or "",
            content=comment.content or "",
            like_count=comment.like_count,
            raw_json=comment.raw_data if isinstance(comment.raw_data, dict) else None,
        )
        db.add(nc)


def _save_posts_batch(
    db: Session,
    collected_posts: list,
    source: MonitorSource,
    source_type: str | None = None,
) -> tuple[dict[str, int], list[int], int, int, int]:
    platform = source.platform
    effective_source_type = source_type or source.source_type

    new_posts, updated_posts, dup_post_ids, dup_count, updated_count = batch_dedup_posts(
        db, platform, collected_posts,
    )

    post_id_map: dict[str, int] = {}
    created_post_ids: list[int] = []

    for existing, collected in updated_posts:
        post_id_map[collected.post_id] = existing.id

    for collected in new_posts:
        content_hash = compute_content_hash(collected.content)
        post = Post(
            platform=collected.platform,
            source_id=source.id,
            source_type=effective_source_type,
            post_id=collected.post_id,
            content_hash=content_hash,
            title=collected.title,
            content=collected.content,
            post_url=collected.post_url,
            author_name=collected.author_name,
            author_profile_url=collected.author_profile_url,
            like_count=collected.like_count,
            comment_count=collected.comment_count,
            collect_count=collected.collect_count,
            publish_time=collected.publish_time,
            is_hot=collected.is_hot,
            raw_data=collected.raw_data,
        )
        db.add(post)
        db.flush()
        post_id_map[collected.post_id] = post.id
        created_post_ids.append(post.id)

        _dual_write_note(db, post)

    if updated_posts:
        db.flush()

    return post_id_map, created_post_ids, len(new_posts), dup_count, updated_count


def _save_comments_and_leads(
    db: Session,
    collected_comments: list,
    source: MonitorSource,
    post_id_map: dict[str, int],
    dup_post_ids: set[str],
    source_type: str | None = None,
) -> tuple[int, int, int]:
    platform = source.platform
    effective_source_type = source_type or source.source_type

    new_comments, dup_comment_count = batch_dedup_comments(
        db, platform, collected_comments, dup_post_ids,
    )

    scoring_service = LeadScoringService()
    inserted_comments = 0
    lead_count = 0

    for collected in new_comments:
        content_hash = compute_content_hash(collected.content)
        comment = Comment(
            platform=collected.platform,
            post_id=collected.post_id,
            comment_id=collected.comment_id,
            content_hash=content_hash,
            user_name=collected.user_name,
            user_profile_url=collected.user_profile_url,
            content=collected.content,
            like_count=collected.like_count,
            publish_time=collected.publish_time,
            raw_data=collected.raw_data,
            is_suspected_demand=False,
        )

        scoring_result = scoring_service.score(collected.content or "")
        comment.is_suspected_demand = scoring_result.is_suspected_demand
        comment.demand_type = scoring_result.demand_type
        comment.risk_level = scoring_result.risk_level

        db.add(comment)
        db.flush()
        inserted_comments += 1

        if scoring_result.is_suspected_demand:
            existing_lead = db.query(Lead).filter(
                Lead.platform == collected.platform,
                Lead.source_comment_id == comment.id,
            ).first()
            if existing_lead is not None:
                continue

            lead_content_hash = compute_content_hash(collected.content)
            is_dup, dup_group_id, dup_reason = check_lead_duplicate(
                db, collected.platform, collected.user_profile_url, collected.content,
            )

            lead = Lead(
                platform=collected.platform,
                source_id=source.id,
                source_type=effective_source_type,
                source_post_id=post_id_map.get(collected.post_id),
                source_comment_id=comment.id,
                user_name=collected.user_name,
                user_profile_url=collected.user_profile_url,
                content_hash=lead_content_hash,
                content=collected.content,
                lead_level=scoring_result.lead_level,
                lead_score=scoring_result.lead_score,
                demand_type=scoring_result.demand_type,
                risk_level=scoring_result.risk_level,
                evidence=scoring_result.evidence,
                reason=scoring_result.reason,
                follow_up_script=scoring_result.follow_up_script,
                status="new",
                is_duplicate=is_dup,
                duplicate_group_id=dup_group_id,
                duplicate_reason=dup_reason,
                comment_publish_time=collected.publish_time,
            )
            db.add(lead)
            lead_count += 1

    return inserted_comments, dup_comment_count, lead_count


def run_monitor_source_crawl(db: Session, source: MonitorSource, crawl_task: CrawlTask | None = None) -> CrawlTask:
    if crawl_task is None:
        crawl_task = create_running_crawl_task(db, source)
    else:
        crawl_task.status = "running"
        crawl_task.progress = "collecting"
        crawl_task.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(crawl_task)

    if _should_use_media_crawler(source):
        return _run_monitor_source_with_media_crawler(db, source, crawl_task)

    try:
        effective_config = inject_cookies_into_config(db, source)
        effective_config["max_posts"] = _get_effective_max_posts(source)

        collector_source = SimpleNamespace(
            source_type=source.source_type,
            platform=source.platform,
            value=source.value,
            config=effective_config,
        )
        collector = CollectorFactory.create(collector_source)
        collector_result = collector.collect(collector_source)

        cutoff = _get_time_range_cutoff(source)
        filtered_posts = _filter_posts_by_time_range(collector_result.posts, cutoff)
        filtered_comments = _filter_comments_by_time_range(collector_result.comments, cutoff)

        update_crawl_task_progress(db, crawl_task, "saving_posts")

        post_id_map, created_post_ids, new_posts_count, dup_posts_count, _updated_posts = _save_posts_batch(
            db, filtered_posts, source,
        )

        update_crawl_task_progress(db, crawl_task, "scoring_leads")

        new_comments_count, dup_comments_count, lead_count = _save_comments_and_leads(
            db, filtered_comments, source, post_id_map, set(),
        )

        discovered_competitor_count = 0
        if source.source_type == "keyword":
            discovery_service = CompetitorDiscoveryService()
            discovered_competitor_count = discovery_service.discover_from_keyword_crawl(
                db=db,
                source_id=source.id,
                source_keyword=source.value,
                post_ids=created_post_ids,
            )

        source.last_crawled_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()

        return mark_crawl_task_success(
            db=db,
            crawl_task=crawl_task,
            post_count=new_posts_count,
            comment_count=new_comments_count,
            lead_count=lead_count,
            discovered_competitor_count=discovered_competitor_count,
            collected_posts=len(collector_result.posts),
            collected_comments=len(collector_result.comments),
            duplicate_post_count=dup_posts_count,
            duplicate_comment_count=dup_comments_count,
        )
    except Exception as error:
        db.rollback()
        sanitized_error = _sanitize_error_message(error)
        error_message = f"crawl failed for source_id={source.id}, source_type={source.source_type}: {sanitized_error}"
        failure_type = classify_failure_type(error)
        return mark_crawl_task_failed(db, crawl_task, error_message, failure_type=failure_type.value)


def _run_monitor_source_with_media_crawler(
    db: Session,
    source: MonitorSource,
    crawl_task: CrawlTask,
) -> CrawlTask:
    from app.collectors.media_crawler.collector import MediaCrawlerCollector
    from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS

    if source.platform not in SUPPORTED_PLATFORMS:
        return mark_crawl_task_failed(
            db,
            crawl_task,
            f"MediaCrawler does not support platform '{source.platform}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_PLATFORMS))}",
            failure_type=FailureType.PLATFORM_NOT_SUPPORTED.value,
        )

    collector = MediaCrawlerCollector()
    try:
        update_crawl_task_progress(db, crawl_task, "collecting")

        effective_config = inject_cookies_into_config(db, source)
        effective_config["max_posts"] = _get_effective_max_posts(source)

        collector_source = SimpleNamespace(
            source_type=source.source_type,
            platform=source.platform,
            value=source.value,
            config=effective_config,
        )
        collector_result = collector.collect(collector_source)

        cutoff = _get_time_range_cutoff(source)
        filtered_posts = _filter_posts_by_time_range(collector_result.posts, cutoff)
        filtered_comments = _filter_comments_by_time_range(collector_result.comments, cutoff)

        update_crawl_task_progress(db, crawl_task, "saving_posts")

        post_id_map, created_post_ids, inserted_posts, dup_posts, _updated_posts = _save_posts_batch(
            db, filtered_posts, source,
        )

        update_crawl_task_progress(db, crawl_task, "scoring_leads")

        inserted_comments, dup_comments, lead_count = _save_comments_and_leads(
            db, filtered_comments, source, post_id_map, set(),
        )

        discovered_competitor_count = 0
        if source.source_type == "keyword" and created_post_ids:
            discovery_service = CompetitorDiscoveryService()
            discovered_competitor_count = discovery_service.discover_from_keyword_crawl(
                db=db,
                source_id=source.id,
                source_keyword=source.value,
                post_ids=created_post_ids,
            )

        source.last_crawled_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()

        return mark_crawl_task_success(
            db=db,
            crawl_task=crawl_task,
            post_count=inserted_posts,
            comment_count=inserted_comments,
            lead_count=lead_count,
            discovered_competitor_count=discovered_competitor_count,
            collected_posts=len(collector_result.posts),
            collected_comments=len(collector_result.comments),
            duplicate_post_count=dup_posts,
            duplicate_comment_count=dup_comments,
        )
    except (CollectionAuthError, CollectionNoDataError, CollectionRequestError, ValueError, ConnectionError) as error:
        db.rollback()
        sanitized_error = _sanitize_error_message(error)
        failure_type = classify_failure_type(error)
        return mark_crawl_task_failed(
            db,
            crawl_task,
            f"[MediaCrawler] {sanitized_error}",
            failure_type=failure_type.value,
        )
    except Exception as error:
        db.rollback()
        sanitized_error = _sanitize_error_message(error)
        failure_type = classify_failure_type(error)
        return mark_crawl_task_failed(
            db,
            crawl_task,
            f"[MediaCrawler] {sanitized_error}",
            failure_type=failure_type.value,
        )
