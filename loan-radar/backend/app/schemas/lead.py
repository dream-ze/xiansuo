from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    source_id: int
    source_type: str
    source_post_id: int | None = None
    source_comment_id: int | None = None
    source_post_title: str | None = None
    source_post_url: str | None = None
    user_name: str | None = None
    content: str | None = None
    lead_level: str
    lead_score: float
    demand_type: str | None = None
    risk_level: str | None = None
    evidence: Any | None = None
    reason: str | None = None
    follow_up_script: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
