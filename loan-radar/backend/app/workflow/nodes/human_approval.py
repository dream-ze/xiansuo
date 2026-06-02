from __future__ import annotations

import logging

from app.workflow.context import NodeResult, WorkflowContext
from app.workflow.engine import PauseWorkflow

logger = logging.getLogger(__name__)


class HumanApprovalNode:
    name = "human_approval"

    async def execute(self, context: WorkflowContext) -> NodeResult:
        risk_gate_output = context.get_node_output("risk_gate")
        auto_approve = risk_gate_output.get("auto_approve", False)

        if auto_approve:
            return NodeResult(
                node_name=self.name,
                success=True,
                output={
                    "approved": True,
                    "approval_method": "auto",
                    "reviewer_id": None,
                    "review_comment": None,
                },
            )

        raise PauseWorkflow(
            reason=f"内容风险等级为 {risk_gate_output.get('risk_level', 'unknown')}，需要人工审核"
        )

    def should_proceed(self, context: WorkflowContext) -> bool:
        risk_gate_output = context.get_node_output("risk_gate")
        return risk_gate_output.get("gate_decision") is not None
