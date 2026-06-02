from __future__ import annotations

from app.workflow.context import NodeResult, WorkflowContext


class RiskGateNode:
    name = "risk_gate"

    AUTO_APPROVE_RISK_LEVELS = {"low"}
    MANUAL_REVIEW_RISK_LEVELS = {"medium", "high", "critical"}

    def __init__(self, *, auto_approve_levels: set[str] | None = None) -> None:
        self._auto_approve_levels = auto_approve_levels or self.AUTO_APPROVE_RISK_LEVELS

    async def execute(self, context: WorkflowContext) -> NodeResult:
        compliance_output = context.get_node_output("compliance_check")
        risk_level = compliance_output.get("risk_level", "low")
        is_compliant = compliance_output.get("is_compliant", True)

        auto_approve = risk_level in self._auto_approve_levels and is_compliant

        return NodeResult(
            node_name=self.name,
            success=True,
            output={
                "auto_approve": auto_approve,
                "risk_level": risk_level,
                "is_compliant": is_compliant,
                "gate_decision": "auto_approved" if auto_approve else "manual_review",
            },
        )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True
