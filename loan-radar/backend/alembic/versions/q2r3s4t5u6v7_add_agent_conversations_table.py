"""add agent conversations table

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa

revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("thread_id", sa.String(128), index=True, nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_agent_conversations_thread_user",
        "agent_conversations",
        ["thread_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_conversations_thread_user", table_name="agent_conversations")
    op.drop_table("agent_conversations")
