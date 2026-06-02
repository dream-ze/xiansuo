from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import shanghai_now


class ScriptEffectiveness(Base):
    __tablename__ = "script_effectiveness"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    script_text: Mapped[str] = mapped_column(Text)
    script_source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rag_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    was_approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    approval_risk_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    crm_outcome: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
