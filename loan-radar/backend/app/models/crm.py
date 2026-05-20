from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, func

from app.core.database import Base


class CrmCustomer(Base):
    __tablename__ = "crm_customers"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, default="lead_conversion", index=True)
    lead_id = Column(Integer, nullable=True, index=True)
    platform = Column(String(50), nullable=True, index=True)
    source_channel = Column(String(100), nullable=True, index=True)
    source_url = Column(String(1000), nullable=True)
    source_post_id = Column(Integer, nullable=True, index=True)
    customer_name = Column(String(255), nullable=True, index=True)
    nickname = Column(String(255), nullable=True, index=True)
    phone = Column(String(100), nullable=True, index=True)
    wechat = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    demand_type = Column(String(100), nullable=True, index=True)
    demand_description = Column(Text, nullable=True)
    intended_amount = Column(Float, nullable=True)
    lead_level = Column(String(10), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    owner_name = Column(String(100), nullable=True, index=True)
    entered_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CrmFollowRecord(Base):
    __tablename__ = "crm_follow_records"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    follow_type = Column(String(50), nullable=False, default="manual")
    content = Column(Text, nullable=False)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
