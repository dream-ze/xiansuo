from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


CRM_CUSTOMER_STATUSES = ["pending", "contacted", "interested", "wechat_added", "applied", "converted", "invalid"]

FOLLOW_TYPE_OPTIONS = ["phone", "wechat", "message", "visit", "other"]

SOURCE_TYPE_OPTIONS = ["manual", "lead_conversion", "import"]

SOURCE_CHANNEL_OPTIONS = [
    "小红书", "抖音", "知乎", "微信", "电话",
    "朋友介绍", "线下", "员工自拓", "其他",
]


class CrmCustomerManualCreate(BaseModel):
    customer_name: str | None = None
    nickname: str | None = None
    phone: str | None = None
    wechat: str | None = None
    source_channel: str | None = None
    demand_type: str | None = None
    demand_description: str | None = None
    intended_amount: float | None = None
    city: str | None = None
    lead_level: str | None = None
    owner_name: str | None = None
    entered_by: str | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class CrmCustomerUpdate(BaseModel):
    customer_name: str | None = None
    nickname: str | None = None
    phone: str | None = None
    wechat: str | None = None
    source_channel: str | None = None
    demand_type: str | None = None
    demand_description: str | None = None
    intended_amount: float | None = None
    city: str | None = None
    lead_level: str | None = None
    status: str | None = None
    owner_name: str | None = None
    entered_by: str | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class CrmCustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str = "lead_conversion"
    lead_id: int | None = None
    platform: str | None = None
    source_channel: str | None = None
    source_url: str | None = None
    source_post_id: int | None = None
    customer_name: str | None = None
    nickname: str | None = None
    phone: str | None = None
    wechat: str | None = None
    city: str | None = None
    demand_type: str | None = None
    demand_description: str | None = None
    intended_amount: float | None = None
    lead_level: str | None = None
    status: str
    owner_name: str | None = None
    entered_by: str | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None
    last_follow_up_at: datetime | None = None
    converted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CrmFollowRecordCreate(BaseModel):
    follow_type: str = "manual"
    content: str
    next_follow_up_at: datetime | None = None


class CrmFollowRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    follow_type: str
    content: str
    next_follow_up_at: datetime | None = None
    created_at: datetime


class LeadConvertToCrmPayload(BaseModel):
    owner_name: str | None = None
    next_follow_up_at: datetime | None = None


class CrmDashboardOut(BaseModel):
    total_customers: int = 0
    lead_conversion_count: int = 0
    manual_count: int = 0
    today_new: int = 0
    today_manual: int = 0
    pending_follow: int = 0
    interested: int = 0
    converted: int = 0
    overdue_follow: int = 0
    today_follow_up_count: int = 0
    tomorrow_follow_up_count: int = 0
    this_week_follow_up_count: int = 0
    status_counts: dict[str, int] = {}
    level_counts: dict[str, int] = {}
