from sqlalchemy import Column, DateTime, Float, Integer, String, func

from app.core.database import Base


class PendingCompetitorAccount(Base):
    __tablename__ = "pending_competitor_accounts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    profile_url = Column(String(1000), nullable=False)
    source_keyword = Column(String(255), nullable=True, index=True)
    source_post_id = Column(Integer, nullable=True, index=True)
    discover_reason = Column(String(1000), nullable=True)
    competitor_score = Column(Float, nullable=False, default=0)
    content_relevance_score = Column(Float, nullable=False, default=0)
    interaction_score = Column(Float, nullable=False, default=0)
    lead_potential_score = Column(Float, nullable=False, default=0)
    risk_score = Column(Float, nullable=False, default=0)
    recent_post_count = Column(Integer, nullable=False, default=0)
    recent_comment_count = Column(Integer, nullable=False, default=0)
    suspected_lead_count = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
