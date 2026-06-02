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
    user_profile_url: str | None = None
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
    crm_customer_id: int | None = None
    crm_opportunity_id: int | None = None
    converted_to_crm_at: datetime | None = None
    is_duplicate: bool = False
    duplicate_group_id: str | None = None
    duplicate_reason: str | None = None
    comment_publish_time: datetime | None = None
    ai_identified: bool = False
    ai_confidence: float | None = None
    ai_demand_summary: str | None = None
    ai_key_evidence: Any | None = None
    ai_reasoning: str | None = None
    workflow_id: str | None = None
    created_at: datetime
    updated_at: datetime
