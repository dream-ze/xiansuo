"""add xhs service layer fields

Revision ID: xhs_svc_001
Revises: 01abeaf58ff5
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = "xhs_svc_001"
down_revision = "01abeaf58ff5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_drafts", sa.Column("platform", sa.String(32), server_default="xhs"), schema=None)
    op.add_column("ai_drafts", sa.Column("body", sa.Text(), server_default=""), schema=None)
    op.add_column("ai_drafts", sa.Column("tags", sa.JSON(), nullable=True), schema=None)
    op.add_column("ai_drafts", sa.Column("source_note_id", sa.Integer(), nullable=True), schema=None)
    op.add_column("ai_drafts", sa.Column("intent", sa.String(32), server_default="publish"), schema=None)
    op.create_index("ix_ai_drafts_platform", "ai_drafts", ["platform"])

    op.add_column("draft_assets", sa.Column("draft_id", sa.Integer(), nullable=True), schema=None)
    op.create_index("ix_draft_assets_draft_id", "draft_assets", ["draft_id"])

    op.add_column("ai_generated_assets", sa.Column("draft_id", sa.Integer(), nullable=True), schema=None)
    op.add_column("ai_generated_assets", sa.Column("model_name", sa.String(128), server_default=""), schema=None)
    op.add_column("ai_generated_assets", sa.Column("params", sa.JSON(), nullable=True), schema=None)
    op.add_column("ai_generated_assets", sa.Column("file_path", sa.Text(), server_default=""), schema=None)

    op.add_column("model_configs", sa.Column("model_type", sa.String(32), server_default="text"), schema=None)
    op.add_column("model_configs", sa.Column("model_name", sa.String(128), server_default=""), schema=None)
    op.add_column("model_configs", sa.Column("encrypted_api_key", sa.Text(), server_default=""), schema=None)
    op.create_index("ix_model_configs_model_type", "model_configs", ["model_type"])

    op.add_column("notifications", sa.Column("body", sa.Text(), server_default=""), schema=None)
    op.add_column("notifications", sa.Column("level", sa.String(24), server_default="info"), schema=None)
    op.add_column("notifications", sa.Column("source_task_id", sa.Integer(), nullable=True), schema=None)
    op.add_column("notifications", sa.Column("source_type", sa.String(64), nullable=True), schema=None)
    op.add_column("notifications", sa.Column("source_id", sa.Integer(), nullable=True), schema=None)


def downgrade() -> None:
    op.drop_column("ai_drafts", "intent")
    op.drop_column("ai_drafts", "source_note_id")
    op.drop_column("ai_drafts", "tags")
    op.drop_column("ai_drafts", "body")
    op.drop_index("ix_ai_drafts_platform", "ai_drafts")
    op.drop_column("ai_drafts", "platform")

    op.drop_index("ix_draft_assets_draft_id", "draft_assets")
    op.drop_column("draft_assets", "draft_id")

    op.drop_column("ai_generated_assets", "file_path")
    op.drop_column("ai_generated_assets", "params")
    op.drop_column("ai_generated_assets", "model_name")
    op.drop_column("ai_generated_assets", "draft_id")

    op.drop_index("ix_model_configs_model_type", "model_configs")
    op.drop_column("model_configs", "encrypted_api_key")
    op.drop_column("model_configs", "model_name")
    op.drop_column("model_configs", "model_type")

    op.drop_column("notifications", "source_id")
    op.drop_column("notifications", "source_type")
    op.drop_column("notifications", "source_task_id")
    op.drop_column("notifications", "level")
    op.drop_column("notifications", "body")
