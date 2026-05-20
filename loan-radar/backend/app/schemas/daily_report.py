from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DailyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_date: date
    platform: str
    source_count: int
    post_count: int
    comment_count: int
    lead_count: int
    a_lead_count: int
    b_lead_count: int
    c_lead_count: int
    d_lead_count: int
    top_demands: Any | None = None
    top_keywords: Any | None = None
    hot_posts: Any | None = None
    content_suggestions: Any | None = None
    follow_up_suggestions: Any | None = None
    risk_warnings: Any | None = None
    a_lead_details: Any | None = None
    typical_evidence: Any | None = None
    discovered_competitors: Any | None = None
    tomorrow_suggestions: Any | None = None
    crm_stats: Any | None = None
    created_at: datetime
    updated_at: datetime
