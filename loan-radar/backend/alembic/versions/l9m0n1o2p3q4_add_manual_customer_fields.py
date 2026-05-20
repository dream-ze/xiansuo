"""add manual customer fields to crm_customers

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-05-19 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "l9m0n1o2p3q4"
down_revision: Union[str, None] = "k8l9m0n1o2p3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    bind = op.get_bind()
    return col in {c["name"] for c in inspect(bind).get_columns(table)}


def _index_exists(table: str, idx: str) -> bool:
    bind = op.get_bind()
    return idx in {i["name"] for i in inspect(bind).get_indexes(table)}


def _constraint_exists(table: str, name: str) -> bool:
    bind = op.get_bind()
    uk = inspect(bind).get_unique_constraints(table)
    return name in {c["name"] for c in uk if "name" in c}


def upgrade() -> None:
    if _constraint_exists("crm_customers", "uq_crm_customers_lead_id"):
        op.drop_constraint("uq_crm_customers_lead_id", "crm_customers", type_="unique")

    for col_name, col_type in [
        ("source_type", sa.String(length=50)),
        ("source_channel", sa.String(length=100)),
        ("customer_name", sa.String(length=255)),
        ("city", sa.String(length=100)),
        ("demand_description", sa.Text()),
        ("intended_amount", sa.Float()),
        ("entered_by", sa.String(length=100)),
        ("last_follow_up_at", sa.DateTime(timezone=True)),
    ]:
        if not _col_exists("crm_customers", col_name):
            op.add_column("crm_customers", sa.Column(col_name, col_type, nullable=True))

    op.execute("UPDATE crm_customers SET source_type = 'lead_conversion' WHERE source_type IS NULL")

    if _col_exists("crm_customers", "source_type"):
        op.alter_column("crm_customers", "source_type", nullable=False)

    for idx_name, cols in [
        ("ix_crm_customers_source_type", ["source_type"]),
        ("ix_crm_customers_source_channel", ["source_channel"]),
        ("ix_crm_customers_customer_name", ["customer_name"]),
    ]:
        if not _index_exists("crm_customers", idx_name):
            op.create_index(op.f(idx_name), "crm_customers", cols, unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_crm_customers_customer_name"), table_name="crm_customers")
    op.drop_index(op.f("ix_crm_customers_source_channel"), table_name="crm_customers")
    op.drop_index(op.f("ix_crm_customers_source_type"), table_name="crm_customers")

    op.drop_column("crm_customers", "last_follow_up_at")
    op.drop_column("crm_customers", "entered_by")
    op.drop_column("crm_customers", "intended_amount")
    op.drop_column("crm_customers", "demand_description")
    op.drop_column("crm_customers", "city")
    op.drop_column("crm_customers", "customer_name")
    op.drop_column("crm_customers", "source_channel")
    op.drop_column("crm_customers", "source_type")

    op.create_unique_constraint("uq_crm_customers_lead_id", "crm_customers", ["lead_id"])
