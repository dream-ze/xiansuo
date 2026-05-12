"""expand crawl tasks for collection api

Revision ID: d8e41b6a1c2f
Revises: ae33606f820e
Create Date: 2026-05-12 18:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e41b6a1c2f"
down_revision: Union[str, None] = "ae33606f820e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("crawl_tasks", "source_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("crawl_tasks", sa.Column("source_value", sa.String(length=1000), nullable=True))
    op.add_column(
        "crawl_tasks",
        sa.Column("limit_count", sa.Integer(), nullable=False, server_default="20"),
    )
    op.add_column(
        "crawl_tasks",
        sa.Column("collected_posts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "crawl_tasks",
        sa.Column("collected_comments", sa.Integer(), nullable=False, server_default="0"),
    )

    op.execute("UPDATE crawl_tasks SET source_value = '' WHERE source_value IS NULL")
    op.execute(
        "UPDATE crawl_tasks SET collected_posts = COALESCE(post_count, 0), collected_comments = COALESCE(comment_count, 0)"
    )

    op.alter_column("crawl_tasks", "source_value", existing_type=sa.String(length=1000), nullable=False)
    op.alter_column("crawl_tasks", "limit_count", server_default=None)
    op.alter_column("crawl_tasks", "collected_posts", server_default=None)
    op.alter_column("crawl_tasks", "collected_comments", server_default=None)


def downgrade() -> None:
    op.drop_column("crawl_tasks", "collected_comments")
    op.drop_column("crawl_tasks", "collected_posts")
    op.drop_column("crawl_tasks", "limit_count")
    op.drop_column("crawl_tasks", "source_value")
    op.alter_column("crawl_tasks", "source_id", existing_type=sa.Integer(), nullable=False)