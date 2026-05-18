from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func

from app.core.database import Base


class CrmCustomer(Base):
    __tablename__ = "crm_customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(100), nullable=True, index=True)
    contact_info = Column(String(500), nullable=True)
    owner_name = Column(String(100), nullable=True, index=True)
    source_lead_id = Column(Integer, nullable=True, unique=True, index=True)
    source_platform = Column(String(50), nullable=True, index=True)
    source_type = Column(String(50), nullable=True, index=True)
    source_post_id = Column(Integer, nullable=True, index=True)
    source_comment_id = Column(Integer, nullable=True, index=True)
    source_summary = Column(Text, nullable=True)
    demand_amount = Column(Float, nullable=True)
    loan_purpose = Column(String(255), nullable=True)
    qualification_summary = Column(Text, nullable=True)
    risk_level = Column(String(50), nullable=True, index=True)
    customer_level = Column(String(10), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="new", index=True)
    evidence = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmOpportunity(Base):
    __tablename__ = "crm_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False, index=True)
    source_lead_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    stage = Column(String(50), nullable=False, default="new_customer", index=True)
    estimated_amount = Column(Float, nullable=True)
    expected_close_date = Column(DateTime(timezone=True), nullable=True, index=True)
    probability = Column(Float, nullable=False, default=0)
    loss_reason = Column(Text, nullable=True)
    next_step = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmFollowUpRecord(Base):
    __tablename__ = "crm_follow_up_records"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False, index=True)
    opportunity_id = Column(Integer, ForeignKey("crm_opportunities.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("crm_contracts.id"), nullable=True, index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    follow_up_type = Column(String(50), nullable=False, default="manual", index=True)
    content = Column(Text, nullable=False)
    customer_feedback = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True, index=True)
    stage_before = Column(String(50), nullable=True)
    stage_after = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmTask(Base):
    __tablename__ = "crm_tasks"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("crm_opportunities.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("crm_contracts.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, default="follow_up", index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    priority = Column(String(50), nullable=False, default="normal", index=True)
    suggestion = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmProduct(Base):
    __tablename__ = "crm_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    product_type = Column(String(100), nullable=True, index=True)
    min_amount = Column(Float, nullable=True)
    max_amount = Column(Float, nullable=True)
    interest_rate_desc = Column(String(255), nullable=True)
    requirements = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmContract(Base):
    __tablename__ = "crm_contracts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False, index=True)
    opportunity_id = Column(Integer, ForeignKey("crm_opportunities.id"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("crm_products.id"), nullable=True, index=True)
    contract_no = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    amount = Column(Float, nullable=False, default=0)
    signed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmReceivablePlan(Base):
    __tablename__ = "crm_receivable_plans"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("crm_contracts.id"), nullable=False, index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    amount = Column(Float, nullable=False, default=0)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    received_amount = Column(Float, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmReceivable(Base):
    __tablename__ = "crm_receivables"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("crm_contracts.id"), nullable=False, index=True)
    receivable_plan_id = Column(Integer, ForeignKey("crm_receivable_plans.id"), nullable=True, index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    amount = Column(Float, nullable=False, default=0)
    received_at = Column(DateTime(timezone=True), nullable=False, index=True)
    payment_method = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
