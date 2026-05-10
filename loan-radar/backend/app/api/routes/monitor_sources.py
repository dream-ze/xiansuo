from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.schemas.monitor_source import (
    MonitorSourceCreate,
    MonitorSourceOut,
    MonitorSourceUpdate,
)
from app.services.monitor_source_service import (
    create_monitor_source,
    delete_monitor_source,
    get_monitor_source,
    list_monitor_sources,
    toggle_monitor_source,
    update_monitor_source,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/monitor-sources", tags=["monitor-sources"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_response("monitor source not found"),
    )


def validation_error_response(error: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_response(str(error)),
    )


@router.post("")
def create_monitor_source_endpoint(
    payload: MonitorSourceCreate,
    db: Session = Depends(get_db),
):
    try:
        monitor_source = create_monitor_source(db, payload)
    except ValueError as error:
        return validation_error_response(error)

    data = MonitorSourceOut.model_validate(monitor_source).model_dump(mode="json")
    return success_response(data)


@router.get("")
def list_monitor_sources_endpoint(
    source_type: str | None = None,
    platform: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        monitor_sources = list_monitor_sources(
            db=db,
            source_type=source_type,
            platform=platform,
            enabled=enabled,
            keyword=keyword,
        )
    except ValueError as error:
        return validation_error_response(error)

    items = [
        MonitorSourceOut.model_validate(monitor_source).model_dump(mode="json")
        for monitor_source in monitor_sources
    ]
    return success_response(items)


@router.get("/{monitor_source_id}")
def get_monitor_source_endpoint(
    monitor_source_id: int,
    db: Session = Depends(get_db),
):
    monitor_source = get_monitor_source(db, monitor_source_id)
    if monitor_source is None:
        return not_found_response()

    data = MonitorSourceOut.model_validate(monitor_source).model_dump(mode="json")
    return success_response(data)


@router.patch("/{monitor_source_id}")
def update_monitor_source_endpoint(
    monitor_source_id: int,
    payload: MonitorSourceUpdate,
    db: Session = Depends(get_db),
):
    monitor_source = get_monitor_source(db, monitor_source_id)
    if monitor_source is None:
        return not_found_response()

    try:
        updated_monitor_source = update_monitor_source(db, monitor_source, payload)
    except ValueError as error:
        return validation_error_response(error)

    data = MonitorSourceOut.model_validate(updated_monitor_source).model_dump(mode="json")
    return success_response(data)


@router.patch("/{monitor_source_id}/toggle")
def toggle_monitor_source_endpoint(
    monitor_source_id: int,
    enabled: Annotated[bool | None, Query()] = None,
    db: Session = Depends(get_db),
):
    monitor_source = get_monitor_source(db, monitor_source_id)
    if monitor_source is None:
        return not_found_response()

    updated_monitor_source = toggle_monitor_source(db, monitor_source, enabled)
    data = MonitorSourceOut.model_validate(updated_monitor_source).model_dump(mode="json")
    return success_response(data)


@router.delete("/{monitor_source_id}")
def delete_monitor_source_endpoint(
    monitor_source_id: int,
    db: Session = Depends(get_db),
):
    monitor_source = get_monitor_source(db, monitor_source_id)
    if monitor_source is None:
        return not_found_response()

    delete_monitor_source(db, monitor_source)
    return success_response({"id": monitor_source_id})
