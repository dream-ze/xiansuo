"""add workflow engine and ai enhancement tables

Revision ID: p1q2r3s4t5u6
Revises: xhs_svc_001
Create Date: 2026-06-01

"""
from alembic import op
import sqlalchemy as sa

revision = "p1q2r3s4t5u6"
down_revision = "xhs_svc_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=True),
        sa.Column("workflow_type", sa.String(64), index=True, nullable=False),
        sa.Column("workflow_id", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("state", sa.String(32), index=True, nullable=False, server_default="pending"),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("current_node", sa.String(64), nullable=True),
        sa.Column("paused_at_node", sa.String(64), nullable=True),
        sa.Column("error_node", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("parent_workflow_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "workflow_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.String(128), index=True, nullable=False),
        sa.Column("node_name", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=True),
        sa.Column("output_snapshot", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column("llm_cost_estimate", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "approval_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("workflow_id", sa.String(128), index=True, nullable=True),
        sa.Column("workflow_type", sa.String(64), nullable=True),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=True),
        sa.Column("content_snapshot", sa.JSON(), server_default="{}"),
        sa.Column("risk_level", sa.String(16), index=True, server_default="medium"),
        sa.Column("compliance_result", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), index=True, server_default="pending"),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "compliance_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("category", sa.String(64), index=True, nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("rule_description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(16), server_default="medium"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "knowledge_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("source_type", sa.String(64), index=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(256), index=True, nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "script_effectiveness",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), index=True, nullable=True),
        sa.Column("script_text", sa.Text(), nullable=False),
        sa.Column("script_source", sa.String(32), nullable=True),
        sa.Column("rag_references", sa.JSON(), nullable=True),
        sa.Column("was_approved", sa.Boolean(), nullable=True),
        sa.Column("approval_risk_level", sa.String(16), nullable=True),
        sa.Column("crm_outcome", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.add_column("leads", sa.Column("ai_identified", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("leads", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column("leads", sa.Column("ai_demand_summary", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("ai_key_evidence", sa.JSON(), nullable=True))
    op.add_column("leads", sa.Column("ai_reasoning", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("workflow_id", sa.String(128), nullable=True))

    op.create_index("ix_leads_ai_identified", "leads", ["ai_identified"])
    op.create_index("ix_leads_workflow_id", "leads", ["workflow_id"])

    op.add_column("ai_drafts", sa.Column("compliance_result", sa.JSON(), nullable=True))
    op.add_column("ai_drafts", sa.Column("risk_level", sa.String(16), nullable=True))
    op.add_column("ai_drafts", sa.Column("approval_status", sa.String(32), server_default="not_required"))
    op.add_column("ai_drafts", sa.Column("workflow_id", sa.String(128), nullable=True))

    op.add_column("publish_jobs", sa.Column("compliance_result", sa.JSON(), nullable=True))
    op.add_column("publish_jobs", sa.Column("risk_level", sa.String(16), nullable=True))
    op.add_column("publish_jobs", sa.Column("approval_status", sa.String(32), server_default="not_required"))
    op.add_column("publish_jobs", sa.Column("workflow_id", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("publish_jobs", "workflow_id")
    op.drop_column("publish_jobs", "approval_status")
    op.drop_column("publish_jobs", "risk_level")
    op.drop_column("publish_jobs", "compliance_result")

    op.drop_column("ai_drafts", "workflow_id")
    op.drop_column("ai_drafts", "approval_status")
    op.drop_column("ai_drafts", "risk_level")
    op.drop_column("ai_drafts", "compliance_result")

    op.drop_index("ix_leads_workflow_id", "leads")
    op.drop_index("ix_leads_ai_identified", "leads")
    op.drop_column("leads", "workflow_id")
    op.drop_column("leads", "ai_reasoning")
    op.drop_column("leads", "ai_key_evidence")
    op.drop_column("leads", "ai_demand_summary")
    op.drop_column("leads", "ai_confidence")
    op.drop_column("leads", "ai_identified")

    op.drop_table("script_effectiveness")
    op.drop_table("knowledge_entries")
    op.drop_table("compliance_rules")
    op.drop_table("approval_queue")
    op.drop_table("workflow_logs")
    op.drop_table("workflow_runs")
