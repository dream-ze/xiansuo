from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CrmCustomerBase(BaseModel):
    name: str
    phone: str | None = None
    contact_info: str | None = None
    owner_name: str | None = None
    demand_amount: float | None = None
    loan_purpose: str | None = None
    qualification_summary: str | None = None
    risk_level: str | None = None
    customer_level: str | None = None
    status: str = "new"
    notes: str | None = None


class CrmCustomerCreate(CrmCustomerBase):
    source_lead_id: int | None = None
    source_platform: str | None = None
    source_type: str | None = None
    source_post_id: int | None = None
    source_comment_id: int | None = None
    source_summary: str | None = None
    evidence: Any | None = None


class CrmCustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    contact_info: str | None = None
    owner_name: str | None = None
    demand_amount: float | None = None
    loan_purpose: str | None = None
    qualification_summary: str | None = None
    risk_level: str | None = None
    customer_level: str | None = None
    status: str | None = None
    notes: str | None = None


class CrmCustomerOut(CrmCustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_lead_id: int | None = None
    source_platform: str | None = None
    source_type: str | None = None
    source_post_id: int | None = None
    source_comment_id: int | None = None
    source_summary: str | None = None
    evidence: Any | None = None
    created_at: datetime
    updated_at: datetime


class CrmOpportunityCreate(BaseModel):
    customer_id: int
    name: str
    owner_name: str | None = None
    stage: str = "new_customer"
    estimated_amount: float | None = None
    expected_close_date: datetime | None = None
    probability: float = 0
    loss_reason: str | None = None
    next_step: str | None = None
    notes: str | None = None


class CrmOpportunityUpdate(BaseModel):
    name: str | None = None
    owner_name: str | None = None
    stage: str | None = None
    estimated_amount: float | None = None
    expected_close_date: datetime | None = None
    probability: float | None = None
    loss_reason: str | None = None
    next_step: str | None = None
    notes: str | None = None


class CrmOpportunityOut(CrmOpportunityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_lead_id: int | None = None
    customer_name: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmFollowUpCreate(BaseModel):
    customer_id: int
    opportunity_id: int | None = None
    contract_id: int | None = None
    owner_name: str | None = None
    follow_up_type: str = "manual"
    content: str
    customer_feedback: str | None = None
    next_action: str | None = None
    next_follow_up_at: datetime | None = None
    stage_before: str | None = None
    stage_after: str | None = None


class CrmFollowUpOut(CrmFollowUpCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str | None = None
    opportunity_name: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmTaskCreate(BaseModel):
    customer_id: int | None = None
    opportunity_id: int | None = None
    contract_id: int | None = None
    title: str
    task_type: str = "follow_up"
    owner_name: str | None = None
    due_at: datetime | None = None
    status: str = "pending"
    priority: str = "normal"
    suggestion: str | None = None


class CrmTaskUpdate(BaseModel):
    title: str | None = None
    task_type: str | None = None
    owner_name: str | None = None
    due_at: datetime | None = None
    status: str | None = None
    priority: str | None = None
    suggestion: str | None = None


class CrmTaskOut(CrmTaskCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str | None = None
    opportunity_name: str | None = None
    is_overdue: bool = False
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CrmProductCreate(BaseModel):
    name: str
    product_type: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    interest_rate_desc: str | None = None
    requirements: str | None = None
    enabled: bool = True
    notes: str | None = None


class CrmProductOut(CrmProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CrmContractCreate(BaseModel):
    customer_id: int
    opportunity_id: int | None = None
    product_id: int | None = None
    contract_no: str | None = None
    title: str
    owner_name: str | None = None
    amount: float = 0
    signed_at: datetime | None = None
    status: str = "draft"
    notes: str | None = None


class CrmContractOut(CrmContractCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmReceivablePlanCreate(BaseModel):
    customer_id: int
    contract_id: int
    owner_name: str | None = None
    amount: float
    due_date: datetime
    status: str = "pending"
    received_amount: float = 0
    notes: str | None = None


class CrmReceivablePlanOut(CrmReceivablePlanCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str | None = None
    contract_title: str | None = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime


class CrmReceivableCreate(BaseModel):
    customer_id: int
    contract_id: int
    receivable_plan_id: int | None = None
    owner_name: str | None = None
    amount: float
    received_at: datetime
    payment_method: str | None = None
    notes: str | None = None


class CrmReceivableOut(CrmReceivableCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str | None = None
    contract_title: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadConvertToCrmIn(BaseModel):
    owner_name: str | None = None
    next_follow_up_at: datetime | None = None


class LeadConvertToCrmOut(BaseModel):
    customer: CrmCustomerOut
    opportunity: CrmOpportunityOut
    task: CrmTaskOut
