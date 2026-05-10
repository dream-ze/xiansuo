from sqlalchemy import Column, Date, DateTime, Integer, JSON, String, func

from app.core.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    source_count = Column(Integer, nullable=False, default=0)
    post_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    lead_count = Column(Integer, nullable=False, default=0)
    a_lead_count = Column(Integer, nullable=False, default=0)
    b_lead_count = Column(Integer, nullable=False, default=0)
    c_lead_count = Column(Integer, nullable=False, default=0)
    d_lead_count = Column(Integer, nullable=False, default=0)
    top_demands = Column(JSON, nullable=True)
    top_keywords = Column(JSON, nullable=True)
    hot_posts = Column(JSON, nullable=True)
    content_suggestions = Column(JSON, nullable=True)
    follow_up_suggestions = Column(JSON, nullable=True)
    risk_warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
