"""add retry fields to crawl_tasks

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-05-15 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crawl_tasks",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "crawl_tasks",
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "crawl_tasks",
        sa.Column("last_error_type", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crawl_tasks", "last_error_type")
    op.drop_column("crawl_tasks", "max_retries")
    op.drop_column("crawl_tasks", "retry_count")
