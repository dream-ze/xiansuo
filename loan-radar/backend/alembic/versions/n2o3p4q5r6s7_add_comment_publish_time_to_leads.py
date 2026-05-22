"""add comment_publish_time to leads

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-05-21 10:30:00.000000

"""

from alembic import op

revision = "n2o3p4q5r6s7"
down_revision = "m1n2o3p4q5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE leads
        ADD COLUMN IF NOT EXISTS comment_publish_time TIMESTAMPTZ NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_leads_comment_publish_time
        ON leads (comment_publish_time);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_leads_comment_publish_time;")
    op.execute(
        """
        ALTER TABLE leads
        DROP COLUMN IF EXISTS comment_publish_time;
        """
    )
