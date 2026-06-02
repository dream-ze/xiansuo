from __future__ import annotations

from typing import Annotated, Any, Literal

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class LeadScoringState(TypedDict, total=False):
    workflow_id: str
    user_id: int | None
    text: str
    platform: str
    source_id: int
    source_type: str
    source_post_id: int | None
    source_comment_id: int | None
    user_name: str | None
    user_profile_url: str | None
    comment_publish_time: Any
    model_config: Any
    api_key: str

    rule_score: int
    rule_pass: bool
    rule_level: str
    rule_matched: list[str]
    rule_demand_type: str
    rule_risk_level: str
    rule_evidence: dict[str, Any]
    rule_reason: str
    rule_follow_up_script: str

    is_potential_lead: bool
    ai_confidence: float
    ai_lead_level: str
    ai_demand_type: str
    ai_urgency: str
    ai_demand_summary: str
    ai_key_evidence: list[str]
    ai_estimated_amount: str | None
    ai_risk_flags: list[str]
    ai_reasoning: str

    lead_id: int | None
    lead_action: str

    node_results: dict[str, dict[str, Any]]
    error: str | None


class ScriptGenerationState(TypedDict, total=False):
    workflow_id: str
    user_id: int | None
    text: str
    demand_type: str
    lead_level: str
    lead_id: int | None
    script_text: str
    model_config: Any
    api_key: str

    rag_references: list[dict[str, Any]]
    rag_rules: list[dict[str, Any]]
    rag_top_scripts: list[dict[str, Any]]
    rag_available: bool

    script_candidates: list[dict[str, Any]]
    script_recommended_index: int
    script_rag_sources: list[str]
    script_metadata: dict[str, Any]

    is_compliant: bool
    compliance_risk_level: str
    compliance_violations: list[dict[str, Any]]
    compliance_suggestions: list[str]
    compliance_auto_fix_available: bool
    compliance_fixed_script: str | None

    auto_approve: bool
    gate_decision: str

    approved: bool
    approval_method: str | None
    reviewer_id: int | None
    review_comment: str | None

    node_results: dict[str, dict[str, Any]]
    error: str | None


class ContentPublishState(TypedDict, total=False):
    workflow_id: str
    user_id: int | None
    title: str
    body: str
    text: str
    script_text: str
    draft_id: int | None
    publish_job_id: int | None
    model_config: Any
    api_key: str

    quality_overall_score: float
    quality_relevance_score: float
    quality_completeness_score: float
    quality_readability_score: float
    quality_issues: list[str]
    quality_suggestions: list[str]

    is_compliant: bool
    compliance_risk_level: str
    compliance_violations: list[dict[str, Any]]
    compliance_suggestions: list[str]
    compliance_auto_fix_available: bool
    compliance_fixed_script: str | None

    auto_approve: bool
    gate_decision: str

    approved: bool
    approval_method: str | None
    reviewer_id: int | None
    review_comment: str | None

    node_results: dict[str, dict[str, Any]]
    error: str | None
