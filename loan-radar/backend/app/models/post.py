from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, UniqueConstraint, func

from app.core.database import Base


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("platform", "post_id", name="uq_posts_platform_post_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    post_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    post_url = Column(String(1000), nullable=True)
    author_name = Column(String(255), nullable=True, index=True)
    author_profile_url = Column(String(1000), nullable=True)
    like_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    collect_count = Column(Integer, nullable=False, default=0)
    publish_time = Column(DateTime(timezone=True), nullable=True, index=True)
    is_hot = Column(Boolean, nullable=False, default=False, index=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
