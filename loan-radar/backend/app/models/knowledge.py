from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import shanghai_now


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    entry_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now, onupdate=shanghai_now)
