"""add schedule fields to monitor sources

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-13 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "monitor_sources",
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "monitor_sources",
        sa.Column("schedule_cron", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "monitor_sources",
        sa.Column("last_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("monitor_sources", "last_scheduled_at")
    op.drop_column("monitor_sources", "schedule_cron")
    op.drop_column("monitor_sources", "schedule_enabled")
