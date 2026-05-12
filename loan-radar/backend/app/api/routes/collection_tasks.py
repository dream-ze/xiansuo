from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.schemas.collection_task import CollectionTaskCreate
from app.schemas.crawl_task import CrawlTaskOut
from app.services.collection_task_service import (
    create_collection_task,
    get_collection_task,
    list_collection_tasks,
    run_collection_task,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/collection/tasks", tags=["collection-tasks"])


def not_found_response() -> JSONResponse:
    return JSONResponse(status_code=404, content=error_response("collection task not found"))


@router.post("")
def create_collection_task_endpoint(
    payload: CollectionTaskCreate,
    db: Session = Depends(get_db),
):
    task = create_collection_task(db, payload)
    return success_response(CrawlTaskOut.model_validate(task).model_dump(mode="json"))


@router.get("")
def list_collection_tasks_endpoint(
    status: str | None = None,
    source_type: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    tasks, total = list_collection_tasks(
        db=db,
        status=status,
        source_type=source_type,
        page=page,
        page_size=page_size,
    )
    items = [CrawlTaskOut.model_validate(task).model_dump(mode="json") for task in tasks]
    return success_response({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/{task_id}")
def get_collection_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = get_collection_task(db, task_id)
    if task is None:
        return not_found_response()
    return success_response(CrawlTaskOut.model_validate(task).model_dump(mode="json"))


@router.post("/{task_id}/run")
def run_collection_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = get_collection_task(db, task_id)
    if task is None:
        return not_found_response()
    if task.status == "running":
        return JSONResponse(status_code=400, content=error_response("collection task is already running"))

    result = run_collection_task(db, task)
    return success_response(CrawlTaskOut.model_validate(result).model_dump(mode="json"))