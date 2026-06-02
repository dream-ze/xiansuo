from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import shanghai_now


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    workflow_type: Mapped[str] = mapped_column(String(64), index=True)
    workflow_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    current_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    paused_at_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_workflow_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now, onupdate=shanghai_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WorkflowLog(Base):
    __tablename__ = "workflow_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(128), index=True)
    node_name: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(32))
    input_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_cost_estimate: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=shanghai_now)
