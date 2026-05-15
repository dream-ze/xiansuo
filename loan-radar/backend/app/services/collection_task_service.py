from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.collectors.base import CollectionAuthError, CollectionNoDataError, CollectionRequestError
from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.post import Post
from app.schemas.collection_task import CollectionTaskCreate
from app.services.competitor_discovery_service import CompetitorDiscoveryService
from app.services.crawl_pipeline_service import _comment_already_exists, _post_already_exists, _sanitize_error_message
from app.services.crawl_task_service import get_crawl_task, mark_crawl_task_failed, mark_crawl_task_success
from app.services.lead_scoring_service import LeadScoringService

SUPPORTED_COLLECTION_SOURCE_TYPES = {"keyword", "account", "post_url"}


def create_collection_task(db: Session, payload: CollectionTaskCreate) -> CrawlTask:
    task = CrawlTask(
        source_id=None,
        source_type=payload.source_type,
        source_value=payload.source_value.strip(),
        platform=payload.platform,
        status="pending",
        limit_count=payload.limit_count,
        post_count=0,
        comment_count=0,
        collected_posts=0,
        collected_comments=0,
        lead_count=0,
        discovered_competitor_count=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_collection_tasks(
    db: Session,
    status: str | None = None,
    source_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CrawlTask], int]:
    query = db.query(CrawlTask).filter(CrawlTask.source_id.is_(None), CrawlTask.source_value != "")

    if status is not None:
        query = query.filter(CrawlTask.status == status)
    if source_type is not None:
        query = query.filter(CrawlTask.source_type == source_type)

    total = query.count()
    items = (
        query.order_by(CrawlTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_collection_task(db: Session, task_id: int) -> CrawlTask | None:
    task = get_crawl_task(db, task_id)
    if task is None or task.source_value in (None, "") or task.source_id is not None:
        return None
    return task


def run_collection_task(db: Session, task: CrawlTask) -> CrawlTask:
    from app.collectors.media_crawler.collector import MediaCrawlerCollector
    from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS

    task.status = "running"
    task.started_at = datetime.now(timezone.utc)
    task.finished_at = None
    task.error_message = None
    task.collected_posts = 0
    task.collected_comments = 0
    task.post_count = 0
    task.comment_count = 0
    task.lead_count = 0
    task.discovered_competitor_count = 0
    db.commit()
    db.refresh(task)

    try:
        if task.source_type not in SUPPORTED_COLLECTION_SOURCE_TYPES:
            raise ValueError(f"unsupported collection task source_type: {task.source_type}")

        if task.platform not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"MediaCrawler does not support platform '{task.platform}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_PLATFORMS))}"
            )

        source = _ensure_collection_monitor_source(db, task)

        collector = MediaCrawlerCollector()
        collector_source = SimpleNamespace(
            source_type=_map_task_source_type(task.source_type),
            platform=task.platform,
            value=task.source_value,
            config={
                "collector_type": "media_crawler",
                "max_posts": task.limit_count,
                "enable_comments": True,
            },
        )
        collector_result = collector.collect(collector_source)

        scoring_service = LeadScoringService()
        post_id_map: dict[str, int] = {}
        created_post_ids: list[int] = []
        inserted_posts = 0
        inserted_comments = 0
        lead_count = 0

        mapped_source_type = _map_task_source_type(task.source_type)

        for collected_post in collector_result.posts:
            if not collected_post.post_id:
                continue

            if _post_already_exists(db, collected_post.platform, collected_post.post_id):
                existing_post = (
                    db.query(Post)
                    .filter(Post.platform == collected_post.platform, Post.post_id == collected_post.post_id)
                    .first()
                )
                if existing_post is not None:
                    post_id_map[collected_post.post_id] = existing_post.id
                continue

            post = Post(
                platform=collected_post.platform,
                source_id=source.id,
                source_type=mapped_source_type,
                post_id=collected_post.post_id,
                title=collected_post.title,
                content=collected_post.content,
                post_url=collected_post.post_url,
                author_name=collected_post.author_name,
                author_profile_url=collected_post.author_profile_url,
                like_count=collected_post.like_count,
                comment_count=collected_post.comment_count,
                collect_count=collected_post.collect_count,
                publish_time=collected_post.publish_time,
                is_hot=collected_post.is_hot,
                raw_data=collected_post.raw_data,
            )
            db.add(post)
            db.flush()
            post_id_map[collected_post.post_id] = post.id
            created_post_ids.append(post.id)
            inserted_posts += 1

        for collected_comment in collector_result.comments:
            if not collected_comment.comment_id:
                continue
            if _comment_already_exists(db, collected_comment.platform, collected_comment.comment_id):
                continue

            comment = Comment(
                platform=collected_comment.platform,
                post_id=collected_comment.post_id,
                comment_id=collected_comment.comment_id,
                user_name=collected_comment.user_name,
                user_profile_url=collected_comment.user_profile_url,
                content=collected_comment.content,
                like_count=collected_comment.like_count,
                publish_time=collected_comment.publish_time,
                raw_data=collected_comment.raw_data,
                is_suspected_demand=False,
            )
            scoring_result = scoring_service.score(collected_comment.content or "")
            comment.is_suspected_demand = scoring_result.is_suspected_demand
            comment.demand_type = scoring_result.demand_type
            comment.risk_level = scoring_result.risk_level
            db.add(comment)
            db.flush()
            inserted_comments += 1

            if scoring_result.is_suspected_demand:
                lead = Lead(
                    platform=collected_comment.platform,
                    source_id=source.id,
                    source_type=mapped_source_type,
                    source_post_id=post_id_map.get(collected_comment.post_id),
                    source_comment_id=comment.id,
                    user_name=collected_comment.user_name,
                    content=collected_comment.content,
                    lead_level=scoring_result.lead_level,
                    lead_score=scoring_result.lead_score,
                    demand_type=scoring_result.demand_type,
                    risk_level=scoring_result.risk_level,
                    evidence=scoring_result.evidence,
                    reason=scoring_result.reason,
                    follow_up_script=scoring_result.follow_up_script,
                    status="new",
                )
                db.add(lead)
                lead_count += 1

        discovered_competitor_count = 0
        if task.source_type == "keyword" and created_post_ids:
            discovery_service = CompetitorDiscoveryService()
            discovered_competitor_count = discovery_service.discover_from_keyword_crawl(
                db=db,
                source_id=source.id,
                source_keyword=task.source_value,
                post_ids=created_post_ids,
            )

        source.last_crawled_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()

        return mark_crawl_task_success(
            db=db,
            crawl_task=task,
            post_count=inserted_posts,
            comment_count=inserted_comments,
            lead_count=lead_count,
            discovered_competitor_count=discovered_competitor_count,
            collected_posts=len(collector_result.posts),
            collected_comments=len(collector_result.comments),
        )
    except (CollectionAuthError, CollectionNoDataError, CollectionRequestError, ValueError) as error:
        db.rollback()
        return mark_crawl_task_failed(
            db,
            task,
            f"[MediaCrawler] {_sanitize_error_message(error)}",
        )
    except Exception as error:
        db.rollback()
        return mark_crawl_task_failed(
            db,
            task,
            f"[MediaCrawler] {_sanitize_error_message(error)}",
        )


def _ensure_collection_monitor_source(db: Session, task: CrawlTask) -> MonitorSource:
    mapped_source_type = _map_task_source_type(task.source_type)
    source = (
        db.query(MonitorSource)
        .filter(
            MonitorSource.platform == task.platform,
            MonitorSource.source_type == mapped_source_type,
            MonitorSource.value == task.source_value,
        )
        .first()
    )
    if source is not None:
        return source

    source = MonitorSource(
        source_type=mapped_source_type,
        platform=task.platform,
        name=f"collection:{task.source_type}:{task.source_value[:48]}",
        value=task.source_value,
        config={
            "collector_type": "media_crawler",
            "mode": "real",
            "max_posts": task.limit_count,
            "enable_comments": True,
            "managed_by": "collection_tasks_api",
        },
        enabled=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def _map_task_source_type(source_type: str) -> str:
    mapping = {
        "keyword": "keyword",
        "account": "competitor_account",
        "post_url": "manual_post",
    }
    return mapping.get(source_type, source_type)
