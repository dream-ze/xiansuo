from __future__ import annotations

from app.rag.query_engine import LlamaIndexQueryEngine
from app.workflow.context import WorkflowContext
from app.workflow.engine import WorkflowEngine
from app.workflow.nodes.rag_retrieve import RagRetrieveNode
from app.workflow.nodes.ai_script_generate import AiScriptGenerateNode
from app.workflow.nodes.compliance_check import ComplianceCheckNode
from app.workflow.nodes.risk_gate import RiskGateNode
from app.workflow.nodes.human_approval import HumanApprovalNode


def create_script_generation_workflow(
    *,
    query_engine: LlamaIndexQueryEngine | None = None,
    structured_llm_client=None,
) -> WorkflowEngine:
    nodes = [
        RagRetrieveNode(query_engine=query_engine),
        AiScriptGenerateNode(structured_llm_client=structured_llm_client),
        ComplianceCheckNode(structured_llm_client=structured_llm_client),
        RiskGateNode(),
        HumanApprovalNode(),
    ]

    return WorkflowEngine(nodes=nodes, name="script_generation")


def create_script_generation_context(
    *,
    text: str,
    demand_type: str = "",
    lead_level: str = "C",
    lead_id: int | None = None,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
) -> WorkflowContext:
    return WorkflowContext(
        workflow_type="script_generation",
        user_id=user_id,
        input_data={
            "text": text,
            "demand_type": demand_type,
            "lead_level": lead_level,
            "lead_id": lead_id,
            "script_text": "",
            "model_config": model_config,
            "api_key": api_key,
        },
    )
