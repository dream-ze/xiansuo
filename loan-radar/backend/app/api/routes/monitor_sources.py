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
from app.services.crawl_task_service import create_queued_crawl_task
from app.services.task_queue import CrawlTaskQueue
from app.schemas.crawl_task import CrawlTaskOut
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


@router.get("/media-crawler/health")
def media_crawler_health_check():
    import os
    from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS, PLATFORM_LABELS

    mc_home = os.getenv("MEDIA_CRAWLER_HOME")
    embedded_mode = bool(mc_home)

    shared_db_info = None
    try:
        from app.collectors.media_crawler.shared_db_reader import is_shared_db_available, _get_raw_db_path
        if is_shared_db_available():
            shared_db_info = {
                "available": True,
                "path": _get_raw_db_path(),
            }
        else:
            shared_db_info = {"available": False}
    except Exception:
        shared_db_info = {"available": False}

    if embedded_mode:
        from pathlib import Path
        home_path = Path(mc_home) if mc_home else None
        mc_available = home_path.is_dir() if home_path else False
        status = "healthy" if mc_available else "misconfigured"
        return success_response({
            "status": status,
            "mode": "embedded",
            "media_crawler_home": mc_home,
            "shared_db": shared_db_info,
            "supported_platforms": [
                {"value": p, "label": PLATFORM_LABELS.get(p, p)}
                for p in sorted(SUPPORTED_PLATFORMS)
            ],
        })

    from app.collectors.media_crawler.bridge import MediaCrawlerBridge
    bridge = MediaCrawlerBridge()
    is_healthy = bridge.health_check()

    return success_response({
        "status": "healthy" if is_healthy else "unreachable",
        "mode": "http_bridge",
        "api_base_url": bridge.api_base_url,
        "shared_db": shared_db_info,
        "supported_platforms": [
            {"value": p, "label": PLATFORM_LABELS.get(p, p)}
            for p in sorted(SUPPORTED_PLATFORMS)
        ],
    })


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

    from app.services.crawl_scheduler import add_source_schedule, remove_source_schedule
    if updated_monitor_source.schedule_enabled and updated_monitor_source.schedule_cron:
        try:
            add_source_schedule(updated_monitor_source.id, updated_monitor_source.schedule_cron)
        except ValueError:
            pass
    else:
        remove_source_schedule(updated_monitor_source.id)

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


@router.post("/{monitor_source_id}/crawl")
def crawl_monitor_source_endpoint(
    monitor_source_id: int,
    db: Session = Depends(get_db),
):
    monitor_source = get_monitor_source(db, monitor_source_id)
    if monitor_source is None:
        return not_found_response()

    crawl_task = create_queued_crawl_task(db, monitor_source)
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


@router.delete("/{monitor_source_id}")
def delete_monitor_source_endpoint(
    monitor_source_id: int,
    db: Session = Depends(get_db),
):
    monitor_source = get_monitor_source(db, monitor_source_id)
    if monitor_source is None:
        return not_found_response()

    from app.services.crawl_scheduler import remove_source_schedule
    remove_source_schedule(monitor_source_id)

    delete_monitor_source(db, monitor_source)
    return success_response({"id": monitor_source_id})


@router.get("/scheduler/status")
def get_scheduler_status_endpoint():
    from app.services.crawl_scheduler import get_scheduler_status
    return success_response(get_scheduler_status())
