from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text, func

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_post_id = Column(Integer, nullable=True, index=True)
    source_comment_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(255), nullable=True, index=True)
    content = Column(Text, nullable=True)
    lead_level = Column(String(10), nullable=False, index=True)
    lead_score = Column(Float, nullable=False, default=0)
    demand_type = Column(String(100), nullable=True, index=True)
    risk_level = Column(String(50), nullable=True, index=True)
    evidence = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    follow_up_script = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="new", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
