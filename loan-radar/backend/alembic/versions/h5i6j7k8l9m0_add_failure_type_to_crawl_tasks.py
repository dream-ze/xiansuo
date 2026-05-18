"""add failure_type to crawl_tasks

Revision ID: h5i6j7k8l9m0
Revises: g3h4i5j6k7l8
Create Date: 2026-05-16 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "h5i6j7k8l9m0"
down_revision = "g3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crawl_tasks",
        sa.Column("failure_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crawl_tasks", "failure_type")
