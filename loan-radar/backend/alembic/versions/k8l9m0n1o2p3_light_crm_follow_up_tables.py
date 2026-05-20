"""light crm follow up tables

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-05-18 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "k8l9m0n1o2p3"
down_revision: Union[str, None] = "j7k8l9m0n1o2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    bind = op.get_bind()
    return col in {c["name"] for c in inspect(bind).get_columns(table)}


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def _index_exists(table: str, idx: str) -> bool:
    bind = op.get_bind()
    return idx in {i["name"] for i in inspect(bind).get_indexes(table)}


def _constraint_exists(table: str, name: str) -> bool:
    bind = op.get_bind()
    fk = inspect(bind).get_foreign_keys(table)
    uk = inspect(bind).get_unique_constraints(table)
    return name in {c["name"] for c in fk if "name" in c} or name in {c["name"] for c in uk if "name" in c}


def upgrade() -> None:
    for t in ["crm_receivables", "crm_receivable_plans", "crm_tasks", "crm_follow_up_records", "crm_contracts", "crm_opportunities", "crm_products"]:
        if _table_exists(t):
            op.drop_table(t)

    for idx_name in ["ix_crm_customers_name", "ix_crm_customers_source_lead_id", "ix_crm_customers_owner_name", "ix_crm_customers_status", "ix_crm_customers_id"]:
        if _index_exists("crm_customers", idx_name):
            op.drop_index(idx_name, table_name="crm_customers")

    for col in ["name", "contact_info", "source_lead_id", "source_platform", "source_type", "source_comment_id", "source_summary", "demand_amount", "loan_purpose", "qualification_summary", "risk_level", "customer_level", "evidence"]:
        if _col_exists("crm_customers", col):
            op.drop_column("crm_customers", col)

    for col_name, col_type in [
        ("lead_id", sa.Integer()),
        ("platform", sa.String(length=50)),
        ("nickname", sa.String(length=255)),
        ("source_url", sa.String(length=1000)),
        ("source_post_id", sa.Integer()),
        ("demand_type", sa.String(length=100)),
        ("lead_level", sa.String(length=10)),
        ("wechat", sa.String(length=100)),
        ("next_follow_up_at", sa.DateTime(timezone=True)),
        ("converted_at", sa.DateTime(timezone=True)),
    ]:
        if not _col_exists("crm_customers", col_name):
            op.add_column("crm_customers", sa.Column(col_name, col_type, nullable=True))

    if not _constraint_exists("crm_customers", "uq_crm_customers_lead_id"):
        op.create_unique_constraint("uq_crm_customers_lead_id", "crm_customers", ["lead_id"])
    for idx_name, cols in [
        ("ix_crm_customers_lead_id", ["lead_id"]),
        ("ix_crm_customers_platform", ["platform"]),
        ("ix_crm_customers_nickname", ["nickname"]),
        ("ix_crm_customers_lead_level", ["lead_level"]),
        ("ix_crm_customers_next_follow_up_at", ["next_follow_up_at"]),
        ("ix_crm_customers_converted_at", ["converted_at"]),
    ]:
        if not _index_exists("crm_customers", idx_name):
            op.create_index(op.f(idx_name), "crm_customers", cols, unique=False)

    if not _table_exists("crm_follow_records"):
        op.create_table(
            "crm_follow_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("customer_id", sa.Integer(), nullable=False),
            sa.Column("follow_type", sa.String(length=50), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_crm_follow_records_id"), "crm_follow_records", ["id"], unique=False)
        op.create_index(op.f("ix_crm_follow_records_customer_id"), "crm_follow_records", ["customer_id"], unique=False)

    if not _col_exists("daily_reports", "crm_stats"):
        op.add_column("daily_reports", sa.Column("crm_stats", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("daily_reports", "crm_stats")
    op.drop_table("crm_follow_records")
    op.drop_column("crm_customers", "converted_at")
    op.drop_column("crm_customers", "next_follow_up_at")
    op.drop_column("crm_customers", "wechat")
    op.drop_column("crm_customers", "lead_level")
    op.drop_column("crm_customers", "demand_type")
    op.drop_column("crm_customers", "source_post_id")
    op.drop_column("crm_customers", "source_url")
    op.drop_column("crm_customers", "nickname")
    op.drop_column("crm_customers", "platform")
    op.drop_column("crm_customers", "lead_id")
