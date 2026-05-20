from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.time import shanghai_now
from app.models import AutoTask, User
from app.schemas.common import paginated

router = APIRouter(prefix="/api/xhs/auto-ops", tags=["xhs-auto-ops"])


class AutoTaskCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    keywords: list[str] = Field(min_length=1, max_length=50)
    pc_account_id: Optional[int] = None
    creator_account_id: Optional[int] = None
    ai_instruction: str = ""
    schedule_type: str = "manual"
    schedule_time: str = ""
    schedule_days: str = ""
    schedule_interval_hours: int = 0


class AutoTaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    keywords: Optional[list[str]] = Field(default=None, min_length=1, max_length=50)
    ai_instruction: Optional[str] = None
    status: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_days: Optional[str] = None
    schedule_interval_hours: Optional[int] = None


def _serialize_task(task: AutoTask) -> dict:
    config = json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
    return {
        "id": task.id,
        "user_id": task.user_id,
        "name": task.name,
        "keywords": config.get("keywords", []),
        "pc_account_id": config.get("pc_account_id"),
        "creator_account_id": config.get("creator_account_id"),
        "ai_instruction": config.get("ai_instruction", ""),
        "status": task.status,
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
        "total_published": config.get("total_published", 0),
        "created_at": task.created_at.isoformat(),
        "schedule_type": config.get("schedule_type", "manual"),
        "schedule_time": config.get("schedule_time", ""),
        "schedule_days": config.get("schedule_days", ""),
        "schedule_interval_hours": config.get("schedule_interval_hours", 0),
    }


@router.get("/tasks")
def list_auto_tasks(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    tasks = db.scalars(
        select(AutoTask)
        .where(AutoTask.user_id == current_user.id)
        .order_by(AutoTask.created_at.desc())
    ).all()
    return paginated([_serialize_task(t) for t in tasks], page, page_size)


@router.post("/tasks")
def create_auto_task(
    payload: AutoTaskCreateRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    config = {
        "keywords": payload.keywords,
        "pc_account_id": payload.pc_account_id,
        "creator_account_id": payload.creator_account_id,
        "ai_instruction": payload.ai_instruction,
        "schedule_type": payload.schedule_type,
        "schedule_time": payload.schedule_time,
        "schedule_days": payload.schedule_days,
        "schedule_interval_hours": payload.schedule_interval_hours,
        "total_published": 0,
    }
    task = AutoTask(
        user_id=current_user.id,
        name=payload.name,
        task_type="auto_publish",
        config=json.dumps(config, ensure_ascii=False),
        status="active",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.patch("/tasks/{task_id}")
def update_auto_task(
    task_id: int,
    payload: AutoTaskUpdateRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    task = db.get(AutoTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    config = json.loads(task.config) if isinstance(task.config, str) else (task.config or {})
    if payload.name is not None:
        task.name = payload.name
    if payload.keywords is not None:
        config["keywords"] = payload.keywords
    if payload.ai_instruction is not None:
        config["ai_instruction"] = payload.ai_instruction
    if payload.status is not None:
        task.status = payload.status
    if payload.schedule_type is not None:
        config["schedule_type"] = payload.schedule_type
    if payload.schedule_time is not None:
        config["schedule_time"] = payload.schedule_time
    if payload.schedule_days is not None:
        config["schedule_days"] = payload.schedule_days
    if payload.schedule_interval_hours is not None:
        config["schedule_interval_hours"] = payload.schedule_interval_hours
    task.config = json.dumps(config, ensure_ascii=False)
    task.updated_at = shanghai_now()
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.delete("/tasks/{task_id}")
def delete_auto_task(
    task_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    task = db.get(AutoTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"id": task_id, "status": "deleted"}


@router.post("/tasks/{task_id}/run")
def run_auto_task(
    task_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    task = db.get(AutoTask, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task.last_run_at = shanghai_now()
    db.commit()
    db.refresh(task)
    return {"auto_task": _serialize_task(task), "keyword": "", "source_note": {}, "draft": {}, "publish_job": {}}


@router.post("/run-due")
def run_due_tasks(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {"executed_count": 0, "failed_count": 0, "results": [], "errors": []}
