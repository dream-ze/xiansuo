from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.models import Notification, User
from app.schemas.common import paginated
from app.utils.response import success_response

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def serialize_notification(n: Notification) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body or n.message or "",
        "level": n.level or n.type or "info",
        "source_task_id": n.source_task_id,
        "source_type": n.source_type,
        "source_id": n.source_id,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
def list_notifications(
    unread: Optional[bool] = None,
    level: Optional[str] = None,
    source_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread is True:
        stmt = stmt.where(Notification.is_read == False)
    if level:
        stmt = stmt.where(Notification.level == level)
    if source_type:
        stmt = stmt.where(Notification.source_type == source_type)
    items = db.scalars(stmt.order_by(Notification.created_at.desc())).all()
    return success_response(paginated([serialize_notification(n) for n in items], page, page_size))


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func
    count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).scalar() or 0
    breakdown = {}
    rows = db.query(Notification.level, func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).group_by(Notification.level).all()
    for level_val, cnt in rows:
        breakdown[level_val] = cnt
    return success_response({"count": count, "breakdown": breakdown})


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return success_response(serialize_notification(n))


@router.post("/read-all")
def mark_all_read(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    unread = db.scalars(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    ).all()
    for n in unread:
        n.is_read = True
    db.commit()
    return success_response({"marked": len(unread)})
