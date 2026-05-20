"""make notes user_id and platform_account_id nullable

Revision ID: m1n2o3p4q5r6
Revises: xhs_svc_001
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "m1n2o3p4q5r6"
down_revision = "xhs_svc_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("notes", "user_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("notes", "platform_account_id", existing_type=sa.Integer(), nullable=True)
    op.execute("UPDATE notes SET user_id = NULL WHERE user_id = 0")
    op.execute("UPDATE notes SET platform_account_id = NULL WHERE platform_account_id = 0")


def downgrade() -> None:
    op.execute("UPDATE notes SET user_id = 0 WHERE user_id IS NULL")
    op.execute("UPDATE notes SET platform_account_id = 0 WHERE platform_account_id IS NULL")
    op.alter_column("notes", "platform_account_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("notes", "user_id", existing_type=sa.Integer(), nullable=False)
