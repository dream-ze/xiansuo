"""add crm closed loop tables

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-05-18 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j7k8l9m0n1o2"
down_revision: Union[str, None] = "i6j7k8l9m0n1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("contact_info", sa.String(length=500), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("source_lead_id", sa.Integer(), nullable=True),
        sa.Column("source_platform", sa.String(length=50), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_post_id", sa.Integer(), nullable=True),
        sa.Column("source_comment_id", sa.Integer(), nullable=True),
        sa.Column("source_summary", sa.Text(), nullable=True),
        sa.Column("demand_amount", sa.Float(), nullable=True),
        sa.Column("loan_purpose", sa.String(length=255), nullable=True),
        sa.Column("qualification_summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("customer_level", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_lead_id"),
    )
    op.create_index(op.f("ix_crm_customers_id"), "crm_customers", ["id"], unique=False)
    op.create_index(op.f("ix_crm_customers_name"), "crm_customers", ["name"], unique=False)
    op.create_index(op.f("ix_crm_customers_owner_name"), "crm_customers", ["owner_name"], unique=False)
    op.create_index(op.f("ix_crm_customers_status"), "crm_customers", ["status"], unique=False)
    op.create_index(op.f("ix_crm_customers_source_lead_id"), "crm_customers", ["source_lead_id"], unique=False)

    op.create_table(
        "crm_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("product_type", sa.String(length=100), nullable=True),
        sa.Column("min_amount", sa.Float(), nullable=True),
        sa.Column("max_amount", sa.Float(), nullable=True),
        sa.Column("interest_rate_desc", sa.String(length=255), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_products_id"), "crm_products", ["id"], unique=False)

    op.create_table(
        "crm_opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("source_lead_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("estimated_amount", sa.Float(), nullable=True),
        sa.Column("expected_close_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("loss_reason", sa.Text(), nullable=True),
        sa.Column("next_step", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_opportunities_id"), "crm_opportunities", ["id"], unique=False)
    op.create_index(op.f("ix_crm_opportunities_customer_id"), "crm_opportunities", ["customer_id"], unique=False)
    op.create_index(op.f("ix_crm_opportunities_stage"), "crm_opportunities", ["stage"], unique=False)

    op.create_table(
        "crm_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("contract_no", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["crm_opportunities.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["crm_products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_contracts_id"), "crm_contracts", ["id"], unique=False)

    op.create_table(
        "crm_follow_up_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("follow_up_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("customer_feedback", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage_before", sa.String(length=50), nullable=True),
        sa.Column("stage_after", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["crm_contracts.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["crm_opportunities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_follow_up_records_id"), "crm_follow_up_records", ["id"], unique=False)

    op.create_table(
        "crm_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("opportunity_id", sa.Integer(), nullable=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["crm_contracts.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["crm_opportunities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_tasks_id"), "crm_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_crm_tasks_owner_name"), "crm_tasks", ["owner_name"], unique=False)
    op.create_index(op.f("ix_crm_tasks_status"), "crm_tasks", ["status"], unique=False)

    op.create_table(
        "crm_receivable_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("received_amount", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["crm_contracts.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_receivable_plans_id"), "crm_receivable_plans", ["id"], unique=False)

    op.create_table(
        "crm_receivables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("receivable_plan_id", sa.Integer(), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["crm_contracts.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["crm_customers.id"]),
        sa.ForeignKeyConstraint(["receivable_plan_id"], ["crm_receivable_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_receivables_id"), "crm_receivables", ["id"], unique=False)

    op.add_column("leads", sa.Column("crm_customer_id", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("crm_opportunity_id", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("converted_to_crm_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_leads_crm_customer_id"), "leads", ["crm_customer_id"], unique=False)
    op.create_index(op.f("ix_leads_crm_opportunity_id"), "leads", ["crm_opportunity_id"], unique=False)
    op.create_index(op.f("ix_leads_converted_to_crm_at"), "leads", ["converted_to_crm_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leads_converted_to_crm_at"), table_name="leads")
    op.drop_index(op.f("ix_leads_crm_opportunity_id"), table_name="leads")
    op.drop_index(op.f("ix_leads_crm_customer_id"), table_name="leads")
    op.drop_column("leads", "converted_to_crm_at")
    op.drop_column("leads", "crm_opportunity_id")
    op.drop_column("leads", "crm_customer_id")
    op.drop_table("crm_receivables")
    op.drop_table("crm_receivable_plans")
    op.drop_table("crm_tasks")
    op.drop_table("crm_follow_up_records")
    op.drop_table("crm_contracts")
    op.drop_table("crm_opportunities")
    op.drop_table("crm_products")
    op.drop_table("crm_customers")
