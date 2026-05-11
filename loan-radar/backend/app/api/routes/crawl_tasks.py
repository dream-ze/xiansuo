from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.schemas.crawl_task import CrawlTaskOut
from app.services.crawl_task_service import (
    get_crawl_task,
    list_crawl_tasks,
    rerun_failed_crawl_task,
)
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

    if crawl_task.status != "failed":
        return validation_error_response("only failed crawl tasks can be rerun")

    try:
        rerun_task = rerun_failed_crawl_task(db, crawl_task)
    except ValueError as error:
        if str(error) == "monitor source not found":
            return JSONResponse(status_code=404, content=error_response(str(error)))
        return validation_error_response(str(error))

    data = CrawlTaskOut.model_validate(rerun_task).model_dump(mode="json")
    return success_response(data)
