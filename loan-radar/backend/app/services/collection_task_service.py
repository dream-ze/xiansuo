from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.collectors.base import CollectionAuthError, CollectionNoDataError, CollectionRequestError
from app.models.crawl_task import CrawlTask
from app.models.monitor_source import MonitorSource
from app.schemas.collection_task import CollectionTaskCreate
from app.services.competitor_discovery_service import CompetitorDiscoveryService
from app.services.crawl_pipeline_service import _sanitize_error_message, _save_comments_and_leads, _save_posts_batch
from app.services.crawl_task_service import (
    get_crawl_task,
    mark_crawl_task_failed,
    mark_crawl_task_success,
    update_crawl_task_progress,
)

SUPPORTED_COLLECTION_SOURCE_TYPES = {"keyword", "account", "post_url"}


def create_collection_task(db: Session, payload: CollectionTaskCreate) -> CrawlTask:
    task = CrawlTask(
        source_id=None,
        source_type=payload.source_type,
        source_value=payload.source_value.strip(),
        platform=payload.platform,
        status="pending",
        progress="queued",
        limit_count=payload.limit_count,
        post_count=0,
        comment_count=0,
        collected_posts=0,
        collected_comments=0,
        lead_count=0,
        discovered_competitor_count=0,
        duplicate_post_count=0,
        duplicate_comment_count=0,
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


def run_collection_task_by_id(db: Session, task_id: int) -> CrawlTask:
    task = get_crawl_task(db, task_id)
    if task is None:
        raise ValueError(f"crawl task {task_id} not found")
    return run_collection_task(db, task)


def run_collection_task(db: Session, task: CrawlTask) -> CrawlTask:
    from app.collectors.media_crawler.collector import MediaCrawlerCollector
    from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS

    task.status = "running"
    task.progress = "collecting"
    task.started_at = datetime.now(timezone.utc)
    task.finished_at = None
    task.error_message = None
    task.collected_posts = 0
    task.collected_comments = 0
    task.post_count = 0
    task.comment_count = 0
    task.lead_count = 0
    task.discovered_competitor_count = 0
    task.duplicate_post_count = 0
    task.duplicate_comment_count = 0
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
        mapped_source_type = _map_task_source_type(task.source_type)

        collector = MediaCrawlerCollector()
        collector_source = SimpleNamespace(
            source_type=mapped_source_type,
            platform=task.platform,
            value=task.source_value,
            config={
                "collector_type": "media_crawler",
                "max_posts": task.limit_count,
                "enable_comments": True,
            },
        )
        collector_result = collector.collect(collector_source)

        update_crawl_task_progress(db, task, "saving_posts")

        post_id_map, created_post_ids, inserted_posts, dup_posts, _updated_posts = _save_posts_batch(
            db, collector_result.posts, source, source_type=mapped_source_type,
        )

        update_crawl_task_progress(db, task, "scoring_leads")

        inserted_comments, dup_comments, lead_count = _save_comments_and_leads(
            db, collector_result.comments, source, post_id_map, set(), source_type=mapped_source_type,
        )

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
            duplicate_post_count=dup_posts,
            duplicate_comment_count=dup_comments,
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
