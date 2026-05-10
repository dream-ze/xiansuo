from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PendingCompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    account_name: str
    profile_url: str
    source_keyword: str | None = None
    source_post_id: int | None = None
    discover_reason: str | None = None
    competitor_score: float
    content_relevance_score: float
    interaction_score: float
    lead_potential_score: float
    risk_score: float
    recent_post_count: int
    recent_comment_count: int
    suspected_lead_count: int
    status: str
    created_at: datetime
    updated_at: datetime
