from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from app.services.retry_service import classify_error, should_retry
from app.services.failure_classifier import classify_failure_type

logger = logging.getLogger(__name__)


class CrawlTaskQueue:
    _instance: CrawlTaskQueue | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._queue: list[int] = []
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._active_task_id: int | None = None
        self._stop_event = threading.Event()

    @classmethod
    def get_instance(cls) -> CrawlTaskQueue:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def enqueue(self, crawl_task_id: int) -> int:
        with self._lock:
            if crawl_task_id in self._queue:
                return len(self._queue)
            self._queue.append(crawl_task_id)
            position = len(self._queue)
        logger.info("crawl task %d enqueued, queue position: %d", crawl_task_id, position)
        self._ensure_worker()
        return position

    def dequeue(self) -> int | None:
        with self._lock:
            if not self._queue:
                return None
            task_id = self._queue.pop(0)
            self._active_task_id = task_id
            return task_id

    def mark_done(self, crawl_task_id: int) -> None:
        with self._lock:
            if self._active_task_id == crawl_task_id:
                self._active_task_id = None

    @property
    def active_task_id(self) -> int | None:
        with self._lock:
            return self._active_task_id

    @property
    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def queue_items(self) -> list[int]:
        with self._lock:
            return list(self._queue)

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="crawl-task-worker",
        )
        self._worker_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _worker_loop(self) -> None:
        logger.info("crawl task worker started")
        while not self._stop_event.is_set():
            task_id = self.dequeue()
            if task_id is None:
                time.sleep(1)
                continue
            try:
                logger.info("processing crawl task %d", task_id)
                _execute_crawl_task_with_retry(task_id)
            except Exception:
                logger.exception("crawl task %d execution failed after all retries", task_id)
            finally:
                self.mark_done(task_id)
        with self._lock:
            self._running = False
        logger.info("crawl task worker stopped")


def _execute_crawl_task_with_retry(crawl_task_id: int) -> None:
    from app.core.database import SessionLocal
    from app.models.crawl_task import CrawlTask
    from app.services.crawl_task_service import get_crawl_task, mark_crawl_task_failed

    max_retries = 3
    retry_count = 0

    while retry_count <= max_retries:
        db = SessionLocal()
        try:
            crawl_task = get_crawl_task(db, crawl_task_id)
            if crawl_task is None:
                logger.error("crawl task %d not found", crawl_task_id)
                return

            max_retries = crawl_task.max_retries
            retry_count = crawl_task.retry_count

            _execute_crawl_task_inner(db, crawl_task)
            return
        except Exception as e:
            db.rollback()
            retry_count += 1

            decision = should_retry(e, retry_count - 1, max_retries)
            error_category = classify_error(e)

            logger.warning(
                "crawl task %d attempt %d failed: %s (category=%s, will_retry=%s)",
                crawl_task_id,
                retry_count,
                str(e)[:200],
                error_category.value,
                decision.should_retry,
            )

            try:
                crawl_task = db.query(CrawlTask).filter(CrawlTask.id == crawl_task_id).first()
                if crawl_task is not None:
                    crawl_task.retry_count = retry_count
                    crawl_task.last_error_type = error_category.value
                    if decision.should_retry:
                        crawl_task.status = "retrying"
                        crawl_task.progress = f"retry_{retry_count}"
                        crawl_task.error_message = f"[attempt {retry_count}] {str(e)[:500]}"
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

            if not decision.should_retry:
                db2 = SessionLocal()
                try:
                    crawl_task = db2.query(CrawlTask).filter(CrawlTask.id == crawl_task_id).first()
                    if crawl_task is not None:
                        failure_type = classify_failure_type(e)
                        mark_crawl_task_failed(
                            db2,
                            crawl_task,
                            f"[{error_category.value}] {str(e)[:500]} (after {retry_count} attempts)",
                            failure_type=failure_type.value,
                        )
                finally:
                    db2.close()
                return

            logger.info("crawl task %d waiting %.1fs before retry %d", crawl_task_id, decision.delay_seconds, retry_count)
            time.sleep(decision.delay_seconds)
        finally:
            try:
                db.close()
            except Exception:
                pass


def _execute_crawl_task_inner(db, crawl_task) -> None:
    if crawl_task.source_id is not None:
        from app.models.monitor_source import MonitorSource
        source = db.query(MonitorSource).filter(MonitorSource.id == crawl_task.source_id).first()
        if source is None:
            logger.error("monitor source %d not found for crawl task %d", crawl_task.source_id, crawl_task.id)
            return
        from app.services.crawl_pipeline_service import run_monitor_source_crawl
        run_monitor_source_crawl(db, source, crawl_task=crawl_task)
    else:
        from app.services.collection_task_service import run_collection_task_by_id
        run_collection_task_by_id(db, crawl_task.id)
