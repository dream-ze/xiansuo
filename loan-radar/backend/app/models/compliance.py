from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import shanghai_now


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    rule_text: Mapped[str] = mapped_column(Text)
    rule_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now, onupdate=shanghai_now)
