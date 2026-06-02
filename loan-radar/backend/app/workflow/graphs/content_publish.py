from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.workflow.state import ContentPublishState
from app.services.structured_llm import StructuredLLMClient
from app.workflow.nodes.ai_quality_eval import QualityEvalResult
from app.workflow.nodes.compliance_check import ComplianceResult, ComplianceViolation

logger = logging.getLogger(__name__)


def _init_state(
    *,
    title: str = "",
    body: str = "",
    draft_id: int | None = None,
    publish_job_id: int | None = None,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
) -> ContentPublishState:
    return ContentPublishState(
        workflow_id=uuid.uuid4().hex[:16],
        user_id=user_id,
        title=title,
        body=body,
        text=f"{title}\n{body}",
        script_text=body,
        draft_id=draft_id,
        publish_job_id=publish_job_id,
        model_config=model_config,
        api_key=api_key,
        quality_overall_score=0.0,
        quality_relevance_score=0.5,
        quality_completeness_score=0.5,
        quality_readability_score=0.5,
        quality_issues=[],
        quality_suggestions=[],
        is_compliant=True,
        compliance_risk_level="low",
        compliance_violations=[],
        compliance_suggestions=[],
        compliance_auto_fix_available=False,
        compliance_fixed_script=None,
        auto_approve=True,
        gate_decision="auto_approved",
        approved=True,
        approval_method=None,
        reviewer_id=None,
        review_comment=None,
        node_results={},
        error=None,
    )


def ai_quality_eval_node(state: ContentPublishState) -> dict[str, Any]:
    structured_llm: StructuredLLMClient | None = state.get("_structured_llm")
    content = state.get("script_text", "") or state.get("body", "") or state.get("text", "")
    topic = state.get("title", "")

    if not content:
        output = QualityEvalResult(
            overall_score=0.0,
            relevance_score=0.0,
            completeness_score=0.0,
            readability_score=0.0,
            issues=["内容为空"],
            suggestions=["请提供内容后再评估"],
        ).model_dump()
        node_results = dict(state.get("node_results", {}))
        node_results["ai_quality_eval"] = output
        output["node_results"] = node_results
        return output

    if structured_llm is None:
        output = _heuristic_eval(content, topic)
        node_results = dict(state.get("node_results", {}))
        node_results["ai_quality_eval"] = output
        output["node_results"] = node_results
        return output

    try:
        from app.workflow.nodes.ai_quality_eval import AiQualityEvalNode

        system_prompt = AiQualityEvalNode._build_system_prompt()
        result, metadata = structured_llm.complete_structured(
            model_config=state["model_config"],
            api_key=state["api_key"],
            system_prompt=system_prompt,
            user_prompt=f"请评估以下内容的质量：\n\n主题：{topic}\n内容：{content}",
            response_model=QualityEvalResult,
            max_retries=1,
        )

        output = {
            "quality_overall_score": result.overall_score,
            "quality_relevance_score": result.relevance_score,
            "quality_completeness_score": result.completeness_score,
            "quality_readability_score": result.readability_score,
            "quality_issues": result.issues,
            "quality_suggestions": result.suggestions,
        }
    except Exception as exc:
        logger.error("AI quality eval failed: %s", exc)
        output = _heuristic_eval(content, topic)
        output["error"] = str(exc)

    node_results = dict(state.get("node_results", {}))
    node_results["ai_quality_eval"] = output
    output["node_results"] = node_results
    return output


def compliance_check_node(state: ContentPublishState) -> dict[str, Any]:
    structured_llm: StructuredLLMClient | None = state.get("_structured_llm")
    content = state.get("script_text", "") or state.get("text", "")

    if not content:
        output = {
            "is_compliant": True,
            "compliance_risk_level": "low",
            "compliance_violations": [],
            "compliance_suggestions": [],
            "compliance_auto_fix_available": False,
            "compliance_fixed_script": None,
        }
        node_results = dict(state.get("node_results", {}))
        node_results["compliance_check"] = output
        output["node_results"] = node_results
        return output

    from app.workflow.nodes.compliance_check import ComplianceCheckNode

    keyword_result = ComplianceCheckNode(
        structured_llm_client=structured_llm
    )._keyword_check(content)

    risk_level = keyword_result.get("risk_level", "low")

    if structured_llm is not None and risk_level in ("medium", "high", "critical"):
        try:
            system_prompt = ComplianceCheckNode._build_system_prompt()
            result, metadata = structured_llm.complete_structured(
                model_config=state["model_config"],
                api_key=state["api_key"],
                system_prompt=system_prompt,
                user_prompt=f"请审核以下内容的合规性：\n\n{content}",
                response_model=ComplianceResult,
                max_retries=1,
            )

            if not result.violations and keyword_result.get("violations"):
                result.violations = [ComplianceViolation(**v) for v in keyword_result["violations"]]
                result.is_compliant = False
                result.risk_level = ComplianceCheckNode._higher_risk(
                    result.risk_level, keyword_result.get("risk_level", "low")
                )

            output = result.model_dump()
        except Exception as exc:
            logger.error("AI compliance check failed: %s", exc)
            output = keyword_result
    else:
        output = keyword_result

    node_results = dict(state.get("node_results", {}))
    node_results["compliance_check"] = output
    output["node_results"] = node_results
    return output


def risk_gate_node(state: ContentPublishState) -> dict[str, Any]:
    risk_level = state.get("compliance_risk_level", "low")
    is_compliant = state.get("is_compliant", True)
    auto_approve_levels = {"low"}
    auto_approve = risk_level in auto_approve_levels and is_compliant

    output = {
        "auto_approve": auto_approve,
        "compliance_risk_level": risk_level,
        "is_compliant": is_compliant,
        "gate_decision": "auto_approved" if auto_approve else "manual_review",
    }

    node_results = dict(state.get("node_results", {}))
    node_results["risk_gate"] = output
    output["node_results"] = node_results
    return output


def should_human_review(state: ContentPublishState) -> str:
    if state.get("auto_approve", True):
        return "auto_approved"
    return "human_approval"


def human_approval_node(state: ContentPublishState) -> dict[str, Any]:
    if state.get("auto_approve", True):
        output = {
            "approved": True,
            "approval_method": "auto",
            "reviewer_id": None,
            "review_comment": None,
        }
        node_results = dict(state.get("node_results", {}))
        node_results["human_approval"] = output
        output["node_results"] = node_results
        return output

    approval_data = interrupt(
        f"内容风险等级为 {state.get('compliance_risk_level', 'unknown')}，需要人工审核"
    )

    approved = approval_data.get("approved", False) if isinstance(approval_data, dict) else False
    output = {
        "approved": approved,
        "approval_method": "manual",
        "reviewer_id": approval_data.get("reviewer_id") if isinstance(approval_data, dict) else None,
        "review_comment": approval_data.get("review_comment") if isinstance(approval_data, dict) else None,
    }

    node_results = dict(state.get("node_results", {}))
    node_results["human_approval"] = output
    output["node_results"] = node_results
    return output


def _heuristic_eval(content: str, topic: str) -> dict[str, Any]:
    issues: list[str] = []
    suggestions: list[str] = []

    if len(content) < 20:
        issues.append("内容过短")
        suggestions.append("建议补充更多细节")
    elif len(content) > 2000:
        issues.append("内容过长")
        suggestions.append("建议精简到 500 字以内")

    relevance = 0.5
    if topic and topic in content:
        relevance = 0.8

    completeness = 0.5
    if len(content) >= 50:
        completeness = 0.7

    readability = 0.6
    if any(p in content for p in ["？", "！", "。", "，"]):
        readability = 0.7

    overall = (relevance + completeness + readability) / 3.0

    return {
        "quality_overall_score": overall,
        "quality_relevance_score": relevance,
        "quality_completeness_score": completeness,
        "quality_readability_score": readability,
        "quality_issues": issues,
        "quality_suggestions": suggestions,
    }


def build_content_publish_graph(
    *,
    structured_llm_client=None,
) -> CompiledStateGraph:
    graph = StateGraph(ContentPublishState)

    def wrapped_quality_eval(state: ContentPublishState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        return ai_quality_eval_node(enriched)

    def wrapped_compliance(state: ContentPublishState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        return compliance_check_node(enriched)

    graph.add_node("ai_quality_eval", wrapped_quality_eval)
    graph.add_node("compliance_check", wrapped_compliance)
    graph.add_node("risk_gate", risk_gate_node)
    graph.add_node("human_approval", human_approval_node)

    graph.set_entry_point("ai_quality_eval")

    graph.add_edge("ai_quality_eval", "compliance_check")
    graph.add_edge("compliance_check", "risk_gate")

    graph.add_conditional_edges(
        "risk_gate",
        should_human_review,
        {
            "auto_approved": END,
            "human_approval": "human_approval",
        },
    )

    graph.add_edge("human_approval", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
