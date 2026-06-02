from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import shanghai_now


class ApprovalQueue(Base):
    __tablename__ = "approval_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    workflow_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content_type: Mapped[str] = mapped_column(String(64))
    content_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    compliance_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
