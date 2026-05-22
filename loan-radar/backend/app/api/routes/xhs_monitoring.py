from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.time import shanghai_now
from app.models import MonitorSource, User
from app.schemas.common import paginated
from app.schemas.crawl_task import CrawlTaskOut
from app.services.crawl_task_service import create_queued_crawl_task
from app.services.task_queue import CrawlTaskQueue

router = APIRouter(prefix="/api/xhs/monitoring", tags=["xhs-monitoring"])


class MonitoringTargetPayload(BaseModel):
    target_type: str = "keyword"
    name: Optional[str] = None
    value: str = Field(min_length=1)
    status: Optional[str] = "active"
    config: Optional[dict] = None


def _serialize_target(source: MonitorSource) -> dict:
    return {
        "id": source.id,
        "platform": source.platform,
        "target_type": source.source_type,
        "name": source.name,
        "value": source.value,
        "status": "active" if source.enabled else "paused",
        "config": source.config or {},
        "last_refreshed_at": source.last_crawled_at.isoformat() if source.last_crawled_at else None,
        "created_at": source.created_at.isoformat(),
        "updated_at": source.updated_at.isoformat(),
    }


@router.get("/targets")
def list_monitoring_targets(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    sources = db.scalars(
        select(MonitorSource)
        .where(MonitorSource.platform == "xhs")
        .order_by(MonitorSource.created_at.desc())
    ).all()
    return paginated([_serialize_target(s) for s in sources], page, page_size)


@router.post("/targets")
def create_monitoring_target(
    payload: MonitoringTargetPayload,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    source = MonitorSource(
        platform="xhs",
        source_type=payload.target_type,
        name=payload.name or payload.value,
        value=payload.value,
        enabled=payload.status != "paused",
        config=payload.config or {},
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _serialize_target(source)


@router.post("/targets/{target_id}/refresh")
def refresh_monitoring_target(
    target_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    source = db.get(MonitorSource, target_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    crawl_task = create_queued_crawl_task(db, source)
    queue = CrawlTaskQueue.get_instance()
    position = queue.enqueue(crawl_task.id)

    source.last_crawled_at = shanghai_now()
    db.commit()
    db.refresh(source)

    crawl_task_data = CrawlTaskOut.model_validate(crawl_task).model_dump(mode="json")

    return {
        "target": _serialize_target(source),
        "task": {
            "id": crawl_task.id,
            "status": crawl_task.status,
            "progress": crawl_task.progress,
            "queue_position": position,
        },
        "crawl_task": crawl_task_data,
    }


@router.delete("/targets/{target_id}")
def delete_monitoring_target(
    target_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    source = db.get(MonitorSource, target_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    db.delete(source)
    db.commit()
    return {"id": target_id, "status": "deleted"}
