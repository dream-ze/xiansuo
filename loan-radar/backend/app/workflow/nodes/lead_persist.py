from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.dedup_service import check_lead_duplicate, compute_content_hash
from app.workflow.context import NodeResult, WorkflowContext

logger = logging.getLogger(__name__)


class LeadPersistNode:
    name = "lead_persist"

    def __init__(self, db: Session) -> None:
        self._db = db

    async def execute(self, context: WorkflowContext) -> NodeResult:
        ai_output = context.get_node_output("ai_lead_identify")
        rule_output = context.get_node_output("rule_prescreen")

        if not ai_output.get("is_potential_lead", False):
            return NodeResult(
                node_name=self.name,
                success=True,
                output={"lead_id": None, "action": "skipped_not_lead"},
            )

        input_data = context.input_data
        content = input_data.get("text", "")
        platform = input_data.get("platform", "xhs")
        source_id = input_data.get("source_id", 0)
        source_type = input_data.get("source_type", "keyword")
        source_post_id = input_data.get("source_post_id")
        source_comment_id = input_data.get("source_comment_id")
        user_name = input_data.get("user_name")
        user_profile_url = input_data.get("user_profile_url")
        comment_publish_time = input_data.get("comment_publish_time")

        content_hash = compute_content_hash(content)

        is_dup, dup_group_id, dup_reason = check_lead_duplicate(
            self._db, platform, user_profile_url, content,
        )

        lead_level = ai_output.get("lead_level", rule_output.get("lead_level", "D"))
        lead_score = int(ai_output.get("confidence", 0) * 100)
        rule_score = rule_output.get("rule_score", 0)
        if rule_score > lead_score:
            lead_score = rule_score

        evidence = rule_output.get("evidence", {})
        if ai_output.get("key_evidence"):
            evidence["ai_key_evidence"] = ai_output["key_evidence"]
        if ai_output.get("estimated_amount"):
            evidence["ai_estimated_amount"] = ai_output["estimated_amount"]

        lead = Lead(
            platform=platform,
            source_id=source_id,
            source_type=source_type,
            source_post_id=source_post_id,
            source_comment_id=source_comment_id,
            user_name=user_name,
            user_profile_url=user_profile_url,
            content_hash=content_hash,
            content=content,
            lead_level=lead_level,
            lead_score=float(lead_score),
            demand_type=ai_output.get("demand_type", rule_output.get("demand_type", "未知")),
            risk_level=ai_output.get("risk_flags") and "high" or rule_output.get("risk_level", "low"),
            evidence=evidence,
            reason=ai_output.get("reasoning") or rule_output.get("reason", ""),
            follow_up_script=rule_output.get("follow_up_script", ""),
            status="new",
            is_duplicate=is_dup,
            duplicate_group_id=dup_group_id,
            duplicate_reason=dup_reason,
            comment_publish_time=comment_publish_time,
            ai_identified=True,
            ai_confidence=ai_output.get("confidence"),
            ai_demand_summary=ai_output.get("demand_summary"),
            ai_key_evidence=ai_output.get("key_evidence"),
            ai_reasoning=ai_output.get("reasoning"),
            workflow_id=context.workflow_id,
        )
        self._db.add(lead)
        self._db.flush()

        return NodeResult(
            node_name=self.name,
            success=True,
            output={"lead_id": lead.id, "lead_level": lead_level, "action": "created"},
        )

    def should_proceed(self, context: WorkflowContext) -> bool:
        return True
