from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, UniqueConstraint, func

from app.core.database import Base


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("platform", "comment_id", name="uq_comments_platform_comment_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    post_id = Column(String(255), nullable=False, index=True)
    comment_id = Column(String(255), nullable=False, index=True)
    content_hash = Column(String(32), nullable=True, index=True)
    user_name = Column(String(255), nullable=True, index=True)
    user_profile_url = Column(String(1000), nullable=True)
    content = Column(Text, nullable=True)
    like_count = Column(Integer, nullable=False, default=0)
    publish_time = Column(DateTime(timezone=True), nullable=True, index=True)
    is_suspected_demand = Column(Boolean, nullable=False, default=False, index=True)
    demand_type = Column(String(100), nullable=True, index=True)
    risk_level = Column(String(50), nullable=True, index=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
