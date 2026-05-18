"""add lead dedup fields

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-05-17 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "i6j7k8l9m0n1"
down_revision = "h5i6j7k8l9m0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("user_profile_url", sa.String(1000), nullable=True))
    op.add_column("leads", sa.Column("content_hash", sa.String(32), nullable=True))
    op.add_column("leads", sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("leads", sa.Column("duplicate_group_id", sa.String(64), nullable=True))
    op.add_column("leads", sa.Column("duplicate_reason", sa.String(255), nullable=True))

    op.create_index("ix_leads_content_hash", "leads", ["content_hash"])
    op.create_index("ix_leads_is_duplicate", "leads", ["is_duplicate"])
    op.create_index("ix_leads_duplicate_group_id", "leads", ["duplicate_group_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_duplicate_group_id", table_name="leads")
    op.drop_index("ix_leads_is_duplicate", table_name="leads")
    op.drop_index("ix_leads_content_hash", table_name="leads")

    op.drop_column("leads", "duplicate_reason")
    op.drop_column("leads", "duplicate_group_id")
    op.drop_column("leads", "is_duplicate")
    op.drop_column("leads", "content_hash")
    op.drop_column("leads", "user_profile_url")
