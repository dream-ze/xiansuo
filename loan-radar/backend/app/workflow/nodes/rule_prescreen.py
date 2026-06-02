from __future__ import annotations

from app.services.lead_scoring_service import LeadScoringService
from app.workflow.context import NodeResult, WorkflowContext


class RulePrescreenNode:
    name = "rule_prescreen"

    def __init__(self) -> None:
        self._scoring_service = LeadScoringService()

    async def execute(self, context: WorkflowContext) -> NodeResult:
        text = context.input_data.get("text", "")
        if not text or not text.strip():
            return NodeResult(
                node_name=self.name,
                success=True,
                output={
                    "pass": False,
                    "rule_score": 0,
                    "matched": [],
                    "lead_level": "D",
                    "reason": "内容为空",
                },
            )

        scoring_result = self._scoring_service.score(text)

        return NodeResult(
            node_name=self.name,
            success=True,
            output={
                "pass": scoring_result.is_suspected_demand,
                "rule_score": scoring_result.lead_score,
                "matched": scoring_result.evidence.get("matched_words", []),
                "lead_level": scoring_result.lead_level,
                "demand_type": scoring_result.demand_type,
                "risk_level": scoring_result.risk_level,
                "evidence": scoring_result.evidence,
                "reason": scoring_result.reason,
                "follow_up_script": scoring_result.follow_up_script,
            },
        )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True
