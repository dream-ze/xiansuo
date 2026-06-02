from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.models import ApprovalQueue, User
from app.schemas.approval import ApprovalQueueOut, ApprovalReviewRequest
from app.schemas.common import paginated
from app.utils.response import success_response

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("")
def list_approvals(
    status_filter: str | None = None,
    risk_level: str | None = None,
    content_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    statement = select(ApprovalQueue).where(ApprovalQueue.user_id == current_user.id)
    if status_filter:
        statement = statement.where(ApprovalQueue.status == status_filter)
    if risk_level:
        statement = statement.where(ApprovalQueue.risk_level == risk_level)
    if content_type:
        statement = statement.where(ApprovalQueue.content_type == content_type)

    total_stmt = select(ApprovalQueue).where(ApprovalQueue.user_id == current_user.id)
    if status_filter:
        total_stmt = total_stmt.where(ApprovalQueue.status == status_filter)

    all_items = db.scalars(
        statement.order_by(ApprovalQueue.created_at.desc(), ApprovalQueue.id.desc())
    ).all()

    items = [ApprovalQueueOut.model_validate(a).model_dump(mode="json") for a in all_items]
    return paginated(items, page, page_size)


@router.get("/pending-count")
def get_pending_count(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    count = db.scalar(
        select(ApprovalQueue).where(
            ApprovalQueue.user_id == current_user.id,
            ApprovalQueue.status == "pending",
        )
    )
    from sqlalchemy import func
    actual_count = db.query(ApprovalQueue).filter(
        ApprovalQueue.user_id == current_user.id,
        ApprovalQueue.status == "pending",
    ).count()
    return success_response({"pending_count": actual_count})


@router.get("/{approval_id}")
def get_approval(
    approval_id: int,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    approval = db.get(ApprovalQueue, approval_id)
    if approval is None or approval.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录未找到")
    return success_response(ApprovalQueueOut.model_validate(approval).model_dump(mode="json"))


@router.post("/{approval_id}/review")
def review_approval(
    approval_id: int,
    payload: ApprovalReviewRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    approval = db.get(ApprovalQueue, approval_id)
    if approval is None or approval.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录未找到")

    if approval.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该记录已审核")

    from datetime import datetime
    approval.status = "approved" if payload.approved else "rejected"
    approval.reviewer_id = current_user.id
    approval.review_comment = payload.review_comment
    approval.reviewed_at = datetime.utcnow()

    if payload.modified_content and payload.approved:
        snapshot = approval.content_snapshot or {}
        snapshot["modified_content"] = payload.modified_content
        approval.content_snapshot = snapshot

    db.commit()
    db.refresh(approval)

    return success_response(ApprovalQueueOut.model_validate(approval).model_dump(mode="json"))
