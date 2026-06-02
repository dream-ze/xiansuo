from __future__ import annotations

from app.workflow.context import WorkflowContext
from app.workflow.engine import WorkflowEngine
from app.workflow.nodes.compliance_check import ComplianceCheckNode
from app.workflow.nodes.risk_gate import RiskGateNode
from app.workflow.nodes.human_approval import HumanApprovalNode
from app.workflow.nodes.ai_quality_eval import AiQualityEvalNode


def create_content_publish_workflow(
    *,
    structured_llm_client=None,
) -> WorkflowEngine:
    nodes = [
        AiQualityEvalNode(structured_llm_client=structured_llm_client),
        ComplianceCheckNode(structured_llm_client=structured_llm_client),
        RiskGateNode(),
        HumanApprovalNode(),
    ]

    return WorkflowEngine(nodes=nodes, name="content_publish")


def create_content_publish_context(
    *,
    title: str = "",
    body: str = "",
    draft_id: int | None = None,
    publish_job_id: int | None = None,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
) -> WorkflowContext:
    return WorkflowContext(
        workflow_type="content_publish",
        user_id=user_id,
        input_data={
            "title": title,
            "body": body,
            "text": f"{title}\n{body}",
            "script_text": body,
            "draft_id": draft_id,
            "publish_job_id": publish_job_id,
            "model_config": model_config,
            "api_key": api_key,
        },
    )
