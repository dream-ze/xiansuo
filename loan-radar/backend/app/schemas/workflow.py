from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowRunOut(BaseModel):
    id: int
    workflow_id: str
    workflow_type: str
    state: str
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    current_node: str | None = None
    paused_at_node: str | None = None
    error_node: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    parent_workflow_id: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class WorkflowLogOut(BaseModel):
    id: int
    workflow_id: str
    node_name: str
    event_type: str
    input_snapshot: dict[str, Any] | None = None
    output_snapshot: dict[str, Any] | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    llm_tokens_used: int | None = None
    llm_cost_estimate: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadScoringRequest(BaseModel):
    text: str = Field(min_length=1, max_length=6000)
    platform: str = Field(default="xhs", max_length=32)
    source_id: int = Field(default=0)
    source_type: str = Field(default="keyword", max_length=50)
    source_post_id: int | None = None
    source_comment_id: int | None = None
    user_name: str | None = None
    user_profile_url: str | None = None


class ScriptGenerationRequest(BaseModel):
    lead_id: int
    demand_type: str = Field(default="", max_length=100)
    lead_level: str = Field(default="C", max_length=1)


class ContentPublishCheckRequest(BaseModel):
    draft_id: int | None = None
    publish_job_id: int | None = None
    title: str = Field(default="", max_length=256)
    body: str = Field(default="", max_length=10000)


class WorkflowResumeRequest(BaseModel):
    approved: bool = True
    review_comment: str | None = None
    modified_content: str | None = None
