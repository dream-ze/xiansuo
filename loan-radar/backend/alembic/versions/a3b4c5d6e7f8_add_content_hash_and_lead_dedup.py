"""add content_hash and lead dedup constraint

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-13 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("content_hash", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_posts_content_hash", "posts", ["content_hash"])

    op.add_column(
        "comments",
        sa.Column("content_hash", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_comments_content_hash", "comments", ["content_hash"])

    op.create_unique_constraint("uq_leads_platform_comment", "leads", ["platform", "source_comment_id"])


def downgrade() -> None:
    op.drop_constraint("uq_leads_platform_comment", "leads", type_="unique")
    op.drop_index("ix_comments_content_hash", table_name="comments")
    op.drop_column("comments", "content_hash")
    op.drop_index("ix_posts_content_hash", table_name="posts")
    op.drop_column("posts", "content_hash")
