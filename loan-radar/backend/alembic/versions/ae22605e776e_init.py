"""init

Revision ID: ae22605e776e
Revises: 
Create Date: 2026-05-10 03:47:08.717326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ae22605e776e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
