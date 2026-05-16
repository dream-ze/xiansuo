"""add lead notes and daily report enhancement fields

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g3h4i5j6k7l8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "daily_reports",
        sa.Column("a_lead_details", sa.JSON(), nullable=True),
    )
    op.add_column(
        "daily_reports",
        sa.Column("typical_evidence", sa.JSON(), nullable=True),
    )
    op.add_column(
        "daily_reports",
        sa.Column("discovered_competitors", sa.JSON(), nullable=True),
    )
    op.add_column(
        "daily_reports",
        sa.Column("tomorrow_suggestions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("daily_reports", "tomorrow_suggestions")
    op.drop_column("daily_reports", "discovered_competitors")
    op.drop_column("daily_reports", "typical_evidence")
    op.drop_column("daily_reports", "a_lead_details")
    op.drop_column("leads", "notes")
