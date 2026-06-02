from __future__ import annotations

from app.workflow.context import WorkflowContext
from app.workflow.engine import WorkflowEngine
from app.workflow.nodes.rule_prescreen import RulePrescreenNode
from app.workflow.nodes.ai_lead_identify import AiLeadIdentifyNode
from app.workflow.nodes.lead_persist import LeadPersistNode


def create_lead_scoring_workflow(
    *,
    db=None,
    structured_llm_client=None,
) -> WorkflowEngine:
    nodes = [
        RulePrescreenNode(),
        AiLeadIdentifyNode(structured_llm_client=structured_llm_client),
    ]
    if db is not None:
        nodes.append(LeadPersistNode(db=db))

    return WorkflowEngine(nodes=nodes, name="lead_scoring")


def create_lead_scoring_context(
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
) -> WorkflowContext:
    return WorkflowContext(
        workflow_type="lead_scoring",
        user_id=user_id,
        input_data={
            "text": text,
            "platform": platform,
            "source_id": source_id,
            "source_type": source_type,
            "source_post_id": source_post_id,
            "source_comment_id": source_comment_id,
            "user_name": user_name,
            "user_profile_url": user_profile_url,
            "comment_publish_time": comment_publish_time,
            "model_config": model_config,
            "api_key": api_key,
        },
    )
