from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import shanghai_now


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(64), default="info")
    title: Mapped[str] = mapped_column(String(256))
    message: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(24), default="info")
    is_read: Mapped[bool] = mapped_column(default=False)
    source_task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
