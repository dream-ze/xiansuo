"""merge_heads

Revision ID: cadae47e7229
Revises: n2o3p4q5r6s7, q2r3s4t5u6v7
Create Date: 2026-06-02 10:40:44.438922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cadae47e7229'
down_revision: Union[str, None] = ('n2o3p4q5r6s7', 'q2r3s4t5u6v7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
