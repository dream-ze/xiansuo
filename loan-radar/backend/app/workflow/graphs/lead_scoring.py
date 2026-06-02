from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.workflow.state import LeadScoringState
from app.services.lead_scoring_service import LeadScoringService
from app.services.structured_llm import StructuredLLMClient
from app.workflow.nodes.ai_lead_identify import LeadIdentifyResult

logger = logging.getLogger(__name__)


def _init_state(
    *,
    text: str,
    platform: str = "xhs",
    source_id: int = 0,
    source_type: str = "keyword",
    source_post_id: int | None = None,
    source_comment_id: int | None = None,
    user_name: str | None = None,
    user_profile_url: str | None = None,
    comment_publish_time=None,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
) -> LeadScoringState:
    return LeadScoringState(
        workflow_id=uuid.uuid4().hex[:16],
        user_id=user_id,
        text=text,
        platform=platform,
        source_id=source_id,
        source_type=source_type,
        source_post_id=source_post_id,
        source_comment_id=source_comment_id,
        user_name=user_name,
        user_profile_url=user_profile_url,
        comment_publish_time=comment_publish_time,
        model_config=model_config,
        api_key=api_key,
        rule_score=0,
        rule_pass=False,
        rule_level="D",
        rule_matched=[],
        rule_demand_type="",
        rule_risk_level="low",
        rule_evidence={},
        rule_reason="",
        rule_follow_up_script="",
        is_potential_lead=False,
        ai_confidence=0.0,
        ai_lead_level="D",
        ai_demand_type="",
        ai_urgency="low",
        ai_demand_summary="",
        ai_key_evidence=[],
        ai_estimated_amount=None,
        ai_risk_flags=[],
        ai_reasoning="",
        lead_id=None,
        lead_action="",
        node_results={},
        error=None,
    )


def rule_prescreen_node(state: LeadScoringState) -> dict[str, Any]:
    text = state.get("text", "")
    if not text or not text.strip():
        return {
            "rule_pass": False,
            "rule_score": 0,
            "rule_matched": [],
            "rule_level": "D",
            "rule_demand_type": "",
            "rule_risk_level": "low",
            "rule_evidence": {},
            "rule_reason": "内容为空",
            "rule_follow_up_script": "",
        }

    service = LeadScoringService()
    result = service.score(text)

    output = {
        "rule_pass": result.is_suspected_demand,
        "rule_score": result.lead_score,
        "rule_matched": result.evidence.get("matched_words", []),
        "rule_level": result.lead_level,
        "rule_demand_type": result.demand_type,
        "rule_risk_level": result.risk_level,
        "rule_evidence": result.evidence,
        "rule_reason": result.reason,
        "rule_follow_up_script": result.follow_up_script,
    }

    node_results = dict(state.get("node_results", {}))
    node_results["rule_prescreen"] = output
    output["node_results"] = node_results

    return output


def should_run_ai(state: LeadScoringState) -> str:
    rule_score = state.get("rule_score", 0)
    if rule_score < 15:
        return "lead_persist"
    return "ai_lead_identify"


def ai_lead_identify_node(state: LeadScoringState) -> dict[str, Any]:
    text = state.get("text", "")
    structured_llm: StructuredLLMClient | None = state.get("_structured_llm")

    if not text or not text.strip():
        return {
            "is_potential_lead": False,
            "ai_confidence": 0.0,
            "ai_lead_level": "D",
            "ai_demand_type": "无效",
            "ai_urgency": "low",
            "ai_demand_summary": "",
            "ai_key_evidence": [],
            "ai_estimated_amount": None,
            "ai_risk_flags": [],
            "ai_reasoning": "内容为空，跳过 AI 识别",
        }

    if structured_llm is None:
        return _fallback_from_rules(state)

    try:
        from app.workflow.nodes.ai_lead_identify import AiLeadIdentifyNode

        system_prompt = AiLeadIdentifyNode._build_system_prompt()
        user_prompt = AiLeadIdentifyNode._build_user_prompt(
            text,
            {
                "rule_score": state.get("rule_score", 0),
                "lead_level": state.get("rule_level", "D"),
                "matched": state.get("rule_matched", []),
                "demand_type": state.get("rule_demand_type", ""),
            },
        )

        result, metadata = structured_llm.complete_structured(
            model_config=state["model_config"],
            api_key=state["api_key"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LeadIdentifyResult,
            max_retries=2,
        )

        output = {
            "is_potential_lead": result.is_potential_lead,
            "ai_confidence": result.confidence,
            "ai_lead_level": result.lead_level,
            "ai_demand_type": result.demand_type,
            "ai_urgency": result.urgency,
            "ai_demand_summary": result.demand_summary,
            "ai_key_evidence": result.key_evidence,
            "ai_estimated_amount": result.estimated_amount,
            "ai_risk_flags": result.risk_flags,
            "ai_reasoning": result.reasoning,
        }

    except Exception as exc:
        logger.error("AI lead identify failed: %s", exc)
        output = _fallback_from_rules(state)
        output["error"] = str(exc)

    node_results = dict(state.get("node_results", {}))
    node_results["ai_lead_identify"] = output
    output["node_results"] = node_results

    return output


def lead_persist_node(state: LeadScoringState) -> dict[str, Any]:
    db = state.get("_db")
    is_potential_lead = state.get("is_potential_lead", False)

    if not is_potential_lead:
        output = {"lead_id": None, "lead_action": "skipped_not_lead"}
        node_results = dict(state.get("node_results", {}))
        node_results["lead_persist"] = output
        output["node_results"] = node_results
        return output

    if db is None:
        output = {"lead_id": None, "lead_action": "skipped_no_db"}
        node_results = dict(state.get("node_results", {}))
        node_results["lead_persist"] = output
        output["node_results"] = node_results
        return output

    from app.models.lead import Lead
    from app.services.dedup_service import check_lead_duplicate, compute_content_hash

    content = state.get("text", "")
    platform = state.get("platform", "xhs")
    content_hash = compute_content_hash(content)

    is_dup, dup_group_id, dup_reason = check_lead_duplicate(
        db, platform, state.get("user_profile_url"), content,
    )

    ai_level = state.get("ai_lead_level", "")
    rule_level = state.get("rule_level", "D")
    lead_level = ai_level or rule_level

    ai_conf = state.get("ai_confidence", 0)
    rule_score = state.get("rule_score", 0)
    lead_score = max(int(ai_conf * 100), rule_score)

    evidence = state.get("rule_evidence", {})
    if state.get("ai_key_evidence"):
        evidence["ai_key_evidence"] = state["ai_key_evidence"]
    if state.get("ai_estimated_amount"):
        evidence["ai_estimated_amount"] = state["ai_estimated_amount"]

    lead = Lead(
        platform=platform,
        source_id=state.get("source_id", 0),
        source_type=state.get("source_type", "keyword"),
        source_post_id=state.get("source_post_id"),
        source_comment_id=state.get("source_comment_id"),
        user_name=state.get("user_name"),
        user_profile_url=state.get("user_profile_url"),
        content_hash=content_hash,
        content=content,
        lead_level=lead_level,
        lead_score=float(lead_score),
        demand_type=state.get("ai_demand_type") or state.get("rule_demand_type", "未知"),
        risk_level="high" if state.get("ai_risk_flags") else state.get("rule_risk_level", "low"),
        evidence=evidence,
        reason=state.get("ai_reasoning") or state.get("rule_reason", ""),
        follow_up_script=state.get("rule_follow_up_script", ""),
        status="new",
        is_duplicate=is_dup,
        duplicate_group_id=dup_group_id,
        duplicate_reason=dup_reason,
        comment_publish_time=state.get("comment_publish_time"),
        ai_identified=True,
        ai_confidence=state.get("ai_confidence"),
        ai_demand_summary=state.get("ai_demand_summary"),
        ai_key_evidence=state.get("ai_key_evidence"),
        ai_reasoning=state.get("ai_reasoning"),
        workflow_id=state.get("workflow_id", ""),
    )
    db.add(lead)
    db.flush()

    output = {"lead_id": lead.id, "lead_level": lead_level, "lead_action": "created"}
    node_results = dict(state.get("node_results", {}))
    node_results["lead_persist"] = output
    output["node_results"] = node_results

    return output


def _fallback_from_rules(state: LeadScoringState) -> dict[str, Any]:
    rule_pass = state.get("rule_pass", False)
    rule_score = state.get("rule_score", 0)
    return {
        "is_potential_lead": rule_pass,
        "ai_confidence": min(rule_score / 100.0, 1.0),
        "ai_lead_level": state.get("rule_level", "D"),
        "ai_demand_type": state.get("rule_demand_type", "未知"),
        "ai_urgency": "high" if rule_score >= 70 else "medium" if rule_score >= 40 else "low",
        "ai_demand_summary": state.get("rule_reason", ""),
        "ai_key_evidence": state.get("rule_matched", []),
        "ai_estimated_amount": None,
        "ai_risk_flags": [],
        "ai_reasoning": "AI 不可用，使用规则引擎结果作为降级方案",
    }


def build_lead_scoring_graph(
    *,
    db=None,
    structured_llm_client=None,
) -> CompiledStateGraph:
    graph = StateGraph(LeadScoringState)

    def wrapped_rule_prescreen(state: LeadScoringState) -> dict:
        return rule_prescreen_node(state)

    def wrapped_ai_identify(state: LeadScoringState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        return ai_lead_identify_node(enriched)

    def wrapped_lead_persist(state: LeadScoringState) -> dict:
        enriched = dict(state)
        enriched["_db"] = db
        return lead_persist_node(enriched)

    graph.add_node("rule_prescreen", wrapped_rule_prescreen)
    graph.add_node("ai_lead_identify", wrapped_ai_identify)
    graph.add_node("lead_persist", wrapped_lead_persist)

    graph.set_entry_point("rule_prescreen")

    graph.add_conditional_edges(
        "rule_prescreen",
        should_run_ai,
        {
            "ai_lead_identify": "ai_lead_identify",
            "lead_persist": "lead_persist",
        },
    )

    graph.add_edge("ai_lead_identify", "lead_persist")
    graph.add_edge("lead_persist", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
