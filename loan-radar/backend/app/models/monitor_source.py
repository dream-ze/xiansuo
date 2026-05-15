from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, func

from app.core.database import Base


class MonitorSource(Base):
    __tablename__ = "monitor_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    value = Column(String(1000), nullable=False)
    config = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    schedule_enabled = Column(Boolean, nullable=False, default=False)
    schedule_cron = Column(String(100), nullable=True)
    last_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
