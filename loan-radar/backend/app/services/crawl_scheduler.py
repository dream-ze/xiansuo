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
_PUBLISH_CHECK_INTERVAL_SECONDS = 60
_COOKIE_CHECK_INTERVAL_HOURS = 2

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


def _run_due_publish_jobs() -> None:
    try:
        from app.services.xhs_scheduler_service import run_due_publish_jobs_once
        result = run_due_publish_jobs_once()
        if result["executed_count"] > 0:
            logger.info("XHS publish scheduler: %d jobs executed, %d failed", result["executed_count"], result["failed_count"])
    except Exception:
        logger.exception("XHS publish scheduler failed")


def _run_due_auto_ops_tasks() -> None:
    try:
        from app.core.database import SessionLocal as _SessionLocal
        from app.core.time import shanghai_now as _shanghai_now
        from app.models import AutoTask, User
        from app.api.routes.xhs_auto_ops import _find_source_note, _generate_draft_content, _create_publish_job
        import json as _json
        from sqlalchemy import select as _select

        db = _SessionLocal()
        try:
            active_tasks = db.scalars(
                _select(AutoTask).where(AutoTask.status == "active")
            ).all()
            executed = 0
            for task in active_tasks:
                config = _json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
                schedule_type = config.get("schedule_type", "manual")
                if schedule_type == "manual":
                    continue
                try:
                    user = db.get(User, task.user_id)
                    if not user:
                        continue
                    keywords = config.get("keywords", [])
                    ai_instruction = config.get("ai_instruction", "")
                    creator_account_id = config.get("creator_account_id")
                    source_note = _find_source_note(db, user.id, keywords)
                    draft = _generate_draft_content(db, user.id, keywords, source_note, ai_instruction)
                    _create_publish_job(db, user.id, draft, creator_account_id)
                    task.last_run_at = _shanghai_now()
                    db.commit()
                    executed += 1
                except Exception:
                    db.rollback()
                    logger.exception("auto-ops scheduled task %d failed", task.id)
            if executed > 0:
                logger.info("XHS auto-ops scheduler: %d tasks executed", executed)
        finally:
            db.close()
    except Exception:
        logger.exception("XHS auto-ops scheduler failed")


def _check_account_cookies() -> None:
    try:
        from app.services.xhs_scheduler_service import check_all_account_cookies_once
        check_all_account_cookies_once()
    except Exception:
        logger.exception("XHS cookie health check failed")


def _notify_expired_cookies() -> None:
    from app.services.cookie_resolution_service import check_and_notify_expired_cookies

    db: Session = SessionLocal()
    try:
        count = check_and_notify_expired_cookies(db)
        if count > 0:
            logger.info("Notified %d expired cookie accounts", count)
    except Exception:
        logger.exception("Cookie expiration notification failed")
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

    _scheduler.add_job(
        _run_due_publish_jobs,
        trigger=IntervalTrigger(seconds=_PUBLISH_CHECK_INTERVAL_SECONDS),
        id="xhs_due_publish_runner",
        name="XHS due publish jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_job(
        _check_account_cookies,
        trigger=IntervalTrigger(hours=_COOKIE_CHECK_INTERVAL_HOURS),
        id="xhs_cookie_health_checker",
        name="XHS cookie health check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_job(
        _notify_expired_cookies,
        trigger=IntervalTrigger(hours=_COOKIE_CHECK_INTERVAL_HOURS),
        id="cookie_expiration_notifier",
        name="Cookie expiration notification",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.add_job(
        _run_due_auto_ops_tasks,
        trigger=IntervalTrigger(hours=1),
        id="xhs_auto_ops_runner",
        name="XHS auto-ops due tasks",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.start()
    logger.info("unified scheduler started (crawl check: %d min, publish check: %d sec, cookie check: %d hr, auto-ops: 1 hr)", _CHECK_INTERVAL_MINUTES, _PUBLISH_CHECK_INTERVAL_SECONDS, _COOKIE_CHECK_INTERVAL_HOURS)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("unified scheduler stopped")
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
