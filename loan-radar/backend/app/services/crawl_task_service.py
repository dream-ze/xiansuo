from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.crawl_task import CrawlTask
from app.models.monitor_source import MonitorSource


def create_queued_crawl_task(db: Session, source: MonitorSource) -> CrawlTask:
    config = source.config or {}
    crawl_task = CrawlTask(
        source_id=source.id,
        source_type=source.source_type,
        source_value=source.value,
        platform=source.platform,
        status="pending",
        progress="queued",
        limit_count=int(config.get("max_posts", 20) or 20),
        max_retries=int(config.get("max_retries", 3) or 3),
        post_count=0,
        comment_count=0,
        collected_posts=0,
        collected_comments=0,
        lead_count=0,
        discovered_competitor_count=0,
        duplicate_post_count=0,
        duplicate_comment_count=0,
    )
    db.add(crawl_task)
    db.commit()
    db.refresh(crawl_task)
    return crawl_task


def create_running_crawl_task(db: Session, source: MonitorSource) -> CrawlTask:
    config = source.config or {}
    crawl_task = CrawlTask(
        source_id=source.id,
        source_type=source.source_type,
        source_value=source.value,
        platform=source.platform,
        status="running",
        progress="collecting",
        limit_count=int(config.get("max_posts", 20) or 20),
        max_retries=int(config.get("max_retries", 3) or 3),
        started_at=datetime.now(timezone.utc),
        post_count=0,
        comment_count=0,
        collected_posts=0,
        collected_comments=0,
        lead_count=0,
        discovered_competitor_count=0,
        duplicate_post_count=0,
        duplicate_comment_count=0,
    )
    db.add(crawl_task)
    db.commit()
    db.refresh(crawl_task)
    return crawl_task


def update_crawl_task_progress(db: Session, crawl_task: CrawlTask, progress: str) -> None:
    crawl_task.progress = progress
    db.commit()


def mark_crawl_task_success(
    db: Session,
    crawl_task: CrawlTask,
    post_count: int,
    comment_count: int,
    lead_count: int,
    discovered_competitor_count: int = 0,
    collected_posts: int | None = None,
    collected_comments: int | None = None,
    duplicate_post_count: int = 0,
    duplicate_comment_count: int = 0,
    error_message: str | None = None,
) -> CrawlTask:
    crawl_task.status = "success"
    crawl_task.progress = "done"
    crawl_task.finished_at = datetime.now(timezone.utc)
    crawl_task.post_count = post_count
    crawl_task.comment_count = comment_count
    crawl_task.collected_posts = post_count if collected_posts is None else collected_posts
    crawl_task.collected_comments = comment_count if collected_comments is None else collected_comments
    crawl_task.lead_count = lead_count
    crawl_task.discovered_competitor_count = discovered_competitor_count
    crawl_task.duplicate_post_count = duplicate_post_count
    crawl_task.duplicate_comment_count = duplicate_comment_count
    crawl_task.error_message = error_message
    db.commit()
    db.refresh(crawl_task)
    return crawl_task


def mark_crawl_task_failed(db: Session, crawl_task: CrawlTask, error_message: str) -> CrawlTask:
    crawl_task.status = "failed"
    crawl_task.progress = "failed"
    crawl_task.finished_at = datetime.now(timezone.utc)
    crawl_task.error_message = error_message
    db.commit()
    db.refresh(crawl_task)
    return crawl_task


def get_crawl_task(db: Session, crawl_task_id: int) -> CrawlTask | None:
    return db.query(CrawlTask).filter(CrawlTask.id == crawl_task_id).first()


def list_crawl_tasks(
    db: Session,
    status: str | None = None,
    source_type: str | None = None,
    platform: str | None = None,
    source_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CrawlTask], int]:
    query = db.query(CrawlTask)

    if status is not None:
        query = query.filter(CrawlTask.status == status)
    if source_type is not None:
        query = query.filter(CrawlTask.source_type == source_type)
    if platform is not None:
        query = query.filter(CrawlTask.platform == platform)
    if source_id is not None:
        query = query.filter(CrawlTask.source_id == source_id)

    total = query.count()
    items = (
        query.order_by(CrawlTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def rerun_failed_crawl_task(db: Session, crawl_task: CrawlTask) -> CrawlTask:
    source = db.query(MonitorSource).filter(MonitorSource.id == crawl_task.source_id).first()
    if source is None:
        raise ValueError("monitor source not found")

    from app.services.crawl_pipeline_service import run_monitor_source_crawl

    return run_monitor_source_crawl(db, source)
