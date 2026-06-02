from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from app.workflow.state import ScriptGenerationState
from app.services.structured_llm import StructuredLLMClient
from app.workflow.nodes.ai_script_generate import ScriptGenerateResult, ScriptCandidate
from app.workflow.nodes.compliance_check import ComplianceResult, ComplianceViolation

logger = logging.getLogger(__name__)


def _init_state(
    *,
    text: str,
    demand_type: str = "",
    lead_level: str = "C",
    lead_id: int | None = None,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
) -> ScriptGenerationState:
    return ScriptGenerationState(
        workflow_id=uuid.uuid4().hex[:16],
        user_id=user_id,
        text=text,
        demand_type=demand_type,
        lead_level=lead_level,
        lead_id=lead_id,
        script_text="",
        model_config=model_config,
        api_key=api_key,
        rag_references=[],
        rag_rules=[],
        rag_top_scripts=[],
        rag_available=False,
        script_candidates=[],
        script_recommended_index=0,
        script_rag_sources=[],
        script_metadata={},
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


def rag_retrieve_node(state: ScriptGenerationState) -> dict[str, Any]:
    query_engine = state.get("_query_engine")

    if query_engine is None:
        output = {
            "rag_references": [],
            "rag_rules": [],
            "rag_top_scripts": [],
            "rag_available": False,
        }
        node_results = dict(state.get("node_results", {}))
        node_results["rag_retrieve"] = output
        output["node_results"] = node_results
        return output

    query = state.get("text", "")
    demand_type = state.get("demand_type", "")
    user_id = state.get("user_id")

    try:
        results = query_engine.retrieve(
            query=query,
            user_id=user_id,
            top_k=5,
            source_types=["material", "platform_rule", "quality_script"],
            filters={"demand_type": demand_type} if demand_type else {},
        )

        references = [r for r in results if r.get("source_type") == "material"]
        rules = [r for r in results if r.get("source_type") == "platform_rule"]
        top_scripts = [r for r in results if r.get("source_type") == "quality_script"]

        output = {
            "rag_references": references,
            "rag_rules": rules,
            "rag_top_scripts": top_scripts,
            "rag_available": True,
        }
    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        output = {
            "rag_references": [],
            "rag_rules": [],
            "rag_top_scripts": [],
            "rag_available": False,
            "error": str(exc),
        }

    node_results = dict(state.get("node_results", {}))
    node_results["rag_retrieve"] = output
    output["node_results"] = node_results
    return output


def ai_script_generate_node(state: ScriptGenerationState) -> dict[str, Any]:
    structured_llm: StructuredLLMClient | None = state.get("_structured_llm")
    text = state.get("text", "")
    demand_type = state.get("demand_type", "")
    lead_level = state.get("lead_level", "C")

    if structured_llm is None:
        return _fallback_script(text, demand_type, lead_level, state)

    try:
        from app.workflow.nodes.ai_script_generate import AiScriptGenerateNode

        rag_output = {
            "references": state.get("rag_references", []),
            "rules": state.get("rag_rules", []),
            "top_scripts": state.get("rag_top_scripts", []),
        }

        system_prompt = AiScriptGenerateNode._build_system_prompt(rag_output)
        user_prompt = AiScriptGenerateNode._build_user_prompt(text, demand_type, lead_level, rag_output)

        result, metadata = structured_llm.complete_structured(
            model_config=state["model_config"],
            api_key=state["api_key"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ScriptGenerateResult,
            max_retries=2,
        )

        output = {
            "script_candidates": [c.model_dump() for c in result.candidates],
            "script_recommended_index": result.recommended_index,
            "script_rag_sources": result.rag_sources,
            "script_metadata": result.generation_metadata,
        }

    except Exception as exc:
        logger.error("AI script generation failed: %s", exc)
        output = _fallback_script(text, demand_type, lead_level, state)
        output["error"] = str(exc)

    node_results = dict(state.get("node_results", {}))
    node_results["ai_script_generate"] = output
    output["node_results"] = node_results
    return output


def compliance_check_node(state: ScriptGenerationState) -> dict[str, Any]:
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


def risk_gate_node(state: ScriptGenerationState) -> dict[str, Any]:
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


def should_human_review(state: ScriptGenerationState) -> str:
    if state.get("auto_approve", True):
        return "auto_approved"
    return "human_approval"


def human_approval_node(state: ScriptGenerationState) -> dict[str, Any]:
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


def _fallback_script(
    text: str,
    demand_type: str,
    lead_level: str,
    state: ScriptGenerationState,
) -> dict[str, Any]:
    if lead_level == "A":
        script = f"看到您有{demand_type}的需求，我先帮您看下征信和负债情况，再判断适合信用贷还是抵押类方案。"
    elif lead_level == "B":
        script = f"您关注的{demand_type}方面，可以先补充一下资金用途和期望金额，我再帮您判断可选方案。"
    elif lead_level == "C":
        script = f"关于{demand_type}，可以先看一份办理条件清单，再判断是否适合申请。"
    else:
        script = "暂不建议直接跟进。"

    output = {
        "script_candidates": [ScriptCandidate(
            script_text=script,
            tone="专业",
            key_selling_points=[],
            compliance_notes=[],
        ).model_dump()],
        "script_recommended_index": 0,
        "script_rag_sources": [],
        "script_metadata": {"fallback": True},
    }

    node_results = dict(state.get("node_results", {}))
    node_results["ai_script_generate"] = output
    output["node_results"] = node_results
    return output


def build_script_generation_graph(
    *,
    query_engine=None,
    structured_llm_client=None,
) -> CompiledStateGraph:
    graph = StateGraph(ScriptGenerationState)

    def wrapped_rag_retrieve(state: ScriptGenerationState) -> dict:
        enriched = dict(state)
        enriched["_query_engine"] = query_engine
        return rag_retrieve_node(enriched)

    def wrapped_ai_script(state: ScriptGenerationState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        return ai_script_generate_node(enriched)

    def wrapped_compliance(state: ScriptGenerationState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        return compliance_check_node(enriched)

    graph.add_node("rag_retrieve", wrapped_rag_retrieve)
    graph.add_node("ai_script_generate", wrapped_ai_script)
    graph.add_node("compliance_check", wrapped_compliance)
    graph.add_node("risk_gate", risk_gate_node)
    graph.add_node("human_approval", human_approval_node)

    graph.set_entry_point("rag_retrieve")

    graph.add_edge("rag_retrieve", "ai_script_generate")
    graph.add_edge("ai_script_generate", "compliance_check")
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
