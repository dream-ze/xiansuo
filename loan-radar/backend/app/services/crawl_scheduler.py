from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.monitor_source import MonitorSource

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_MINUTES = 1

_scheduler: BackgroundScheduler | None = None


def _cron_trigger_from_expression(cron_expr: str) -> CronTrigger:
    parts = cron_expr.strip().split()
    if len(parts) == 5:
        return CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])
    if len(parts) == 6:
        return CronTrigger(second=parts[0], minute=parts[1], hour=parts[2], day=parts[3], month=parts[4], day_of_week=parts[5])
    raise ValueError(f"invalid cron expression: {cron_expr!r}, expected 5 or 6 fields")


def _check_and_enqueue_scheduled_sources() -> None:
    from app.services.crawl_task_service import create_queued_crawl_task
    from app.services.task_queue import CrawlTaskQueue

    db: Session = SessionLocal()
    try:
        sources = (
            db.query(MonitorSource)
            .filter(
                MonitorSource.enabled.is_(True),
                MonitorSource.schedule_enabled.is_(True),
            )
            .all()
        )

        if not sources:
            return

        queue = CrawlTaskQueue.get_instance()
        now = datetime.now(timezone.utc)

        for source in sources:
            cron_expr = source.schedule_cron
            if not cron_expr:
                continue

            try:
                trigger = _cron_trigger_from_expression(cron_expr)
            except ValueError:
                logger.warning("invalid cron for source %d: %s", source.id, cron_expr)
                continue

            next_fire = trigger.get_next_fire_time(None, now)
            if next_fire is None:
                continue

            if source.last_scheduled_at is not None:
                from dateutil.parser import isoparse as _parse_dt
                last_sched = source.last_scheduled_at
                if hasattr(last_sched, "tzinfo") and last_sched.tzinfo is None:
                    last_sched = last_sched.replace(tzinfo=timezone.utc)
                diff = (now - last_sched).total_seconds()
                if diff < 30:
                    continue

            try:
                crawl_task = create_queued_crawl_task(db, source)
                position = queue.enqueue(crawl_task.id)
                source.last_scheduled_at = now
                db.commit()
                logger.info("scheduled source %d enqueued as task %d, position %d", source.id, crawl_task.id, position)
            except Exception:
                db.rollback()
                logger.exception("failed to enqueue scheduled source %d", source.id)
    except Exception:
        logger.exception("scheduled source check failed")
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("scheduler already running")
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        _check_and_enqueue_scheduled_sources,
        trigger=IntervalTrigger(minutes=_CHECK_INTERVAL_MINUTES),
        id="scheduled_source_check",
        name="Check scheduled monitor sources",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("crawl scheduler started, check interval: %d min", _CHECK_INTERVAL_MINUTES)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("crawl scheduler stopped")
    _scheduler = None


def add_source_schedule(source_id: int, cron_expr: str) -> None:
    if _scheduler is None:
        return
    job_id = f"source_schedule_{source_id}"
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass
    trigger = _cron_trigger_from_expression(cron_expr)
    _scheduler.add_job(
        _enqueue_single_source,
        trigger=trigger,
        id=job_id,
        name=f"Schedule source {source_id}",
        replace_existing=True,
        args=[source_id],
    )
    logger.info("added cron schedule for source %d: %s", source_id, cron_expr)


def remove_source_schedule(source_id: int) -> None:
    if _scheduler is None:
        return
    job_id = f"source_schedule_{source_id}"
    try:
        _scheduler.remove_job(job_id)
        logger.info("removed schedule for source %d", source_id)
    except Exception:
        pass


def _enqueue_single_source(source_id: int) -> None:
    from app.services.crawl_task_service import create_queued_crawl_task
    from app.services.task_queue import CrawlTaskQueue

    db: Session = SessionLocal()
    try:
        source = db.query(MonitorSource).filter(MonitorSource.id == source_id).first()
        if source is None or not source.enabled or not source.schedule_enabled:
            return

        crawl_task = create_queued_crawl_task(db, source)
        queue = CrawlTaskQueue.get_instance()
        position = queue.enqueue(crawl_task.id)
        source.last_scheduled_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("cron-triggered source %d enqueued as task %d, position %d", source_id, crawl_task.id, position)
    except Exception:
        db.rollback()
        logger.exception("failed to enqueue cron-triggered source %d", source_id)
    finally:
        db.close()


def get_scheduler_status() -> dict:
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": next_run,
        })
    return {"running": True, "jobs": jobs}
