"""add progress and duplicate counts to crawl tasks

Revision ID: e1f2a3b4c5d6
Revises: d8e41b6a1c2f
Create Date: 2026-05-13 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d8e41b6a1c2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crawl_tasks",
        sa.Column("progress", sa.String(length=50), nullable=True, server_default="queued"),
    )
    op.add_column(
        "crawl_tasks",
        sa.Column("duplicate_post_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "crawl_tasks",
        sa.Column("duplicate_comment_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("crawl_tasks", "duplicate_comment_count")
    op.drop_column("crawl_tasks", "duplicate_post_count")
    op.drop_column("crawl_tasks", "progress")
