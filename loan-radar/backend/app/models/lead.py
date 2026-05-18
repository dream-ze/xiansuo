from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint, func

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("platform", "source_comment_id", name="uq_leads_platform_comment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_post_id = Column(Integer, nullable=True, index=True)
    source_comment_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(255), nullable=True, index=True)
    user_profile_url = Column(String(1000), nullable=True)
    content_hash = Column(String(32), nullable=True, index=True)
    content = Column(Text, nullable=True)
    lead_level = Column(String(10), nullable=False, index=True)
    lead_score = Column(Float, nullable=False, default=0)
    demand_type = Column(String(100), nullable=True, index=True)
    risk_level = Column(String(50), nullable=True, index=True)
    evidence = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    follow_up_script = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="new", index=True)
    notes = Column(Text, nullable=True)
    crm_customer_id = Column(Integer, nullable=True, index=True)
    crm_opportunity_id = Column(Integer, nullable=True, index=True)
    converted_to_crm_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_duplicate = Column(Boolean, nullable=False, default=False, index=True)
    duplicate_group_id = Column(String(64), nullable=True, index=True)
    duplicate_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
