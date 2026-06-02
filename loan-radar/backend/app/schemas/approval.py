from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ApprovalQueueOut(BaseModel):
    id: int
    user_id: int
    workflow_id: str | None = None
    workflow_type: str | None = None
    content_type: str
    content_id: int | None = None
    content_snapshot: dict[str, Any] = {}
    risk_level: str = "medium"
    compliance_result: dict[str, Any] | None = None
    status: str = "pending"
    reviewer_id: int | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalReviewRequest(BaseModel):
    approved: bool
    review_comment: str | None = None
    modified_content: str | None = None
