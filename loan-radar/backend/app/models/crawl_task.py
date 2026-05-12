from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_value = Column(String(1000), nullable=True)
    platform = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    limit_count = Column(Integer, nullable=False, default=20)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    post_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    collected_posts = Column(Integer, nullable=False, default=0)
    collected_comments = Column(Integer, nullable=False, default=0)
    lead_count = Column(Integer, nullable=False, default=0)
    discovered_competitor_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
