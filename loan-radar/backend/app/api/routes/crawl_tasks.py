from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.schemas.crawl_task import CrawlTaskOut
from app.services.crawl_task_service import (
    get_crawl_task,
    list_crawl_tasks,
)
from app.services.task_queue import CrawlTaskQueue
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/crawl-tasks", tags=["crawl-tasks"])


def not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_response("crawl task not found"),
    )


def validation_error_response(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_response(message),
    )


@router.get("")
def list_crawl_tasks_endpoint(
    status: str | None = None,
    source_type: str | None = None,
    platform: str | None = None,
    source_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    crawl_tasks, total = list_crawl_tasks(
        db=db,
        status=status,
        source_type=source_type,
        platform=platform,
        source_id=source_id,
        page=page,
        page_size=page_size,
    )
    data = [
        CrawlTaskOut.model_validate(crawl_task).model_dump(mode="json")
        for crawl_task in crawl_tasks
    ]
    return success_response(
        {
            "items": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/{crawl_task_id}")
def get_crawl_task_endpoint(
    crawl_task_id: int,
    db: Session = Depends(get_db),
):
    crawl_task = get_crawl_task(db, crawl_task_id)
    if crawl_task is None:
        return not_found_response()

    data = CrawlTaskOut.model_validate(crawl_task).model_dump(mode="json")
    return success_response(data)


@router.post("/{crawl_task_id}/rerun")
def rerun_crawl_task_endpoint(
    crawl_task_id: int,
    db: Session = Depends(get_db),
):
    crawl_task = get_crawl_task(db, crawl_task_id)
    if crawl_task is None:
        return not_found_response()

    if crawl_task.status not in ("failed", "success", "retrying"):
        return validation_error_response("only failed, completed or retrying crawl tasks can be rerun")

    crawl_task.status = "pending"
    crawl_task.progress = "queued"
    crawl_task.error_message = None
    crawl_task.finished_at = None
    crawl_task.retry_count = 0
    crawl_task.last_error_type = None
    db.commit()
    db.refresh(crawl_task)

    queue = CrawlTaskQueue.get_instance()
    position = queue.enqueue(crawl_task.id)

    data = CrawlTaskOut.model_validate(crawl_task).model_dump(mode="json")
    return JSONResponse(
        status_code=202,
        content=success_response({
            **data,
            "queue_position": position,
        }),
    )
