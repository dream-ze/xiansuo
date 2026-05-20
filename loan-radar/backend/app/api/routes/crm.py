from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.models.crm import CrmCustomer, CrmFollowRecord
from app.schemas.crm import (
    CRM_CUSTOMER_STATUSES,
    CrmCustomerManualCreate,
    CrmCustomerOut,
    CrmCustomerUpdate,
    CrmFollowRecordCreate,
    CrmFollowRecordOut,
)
from app.services.crm_service import apply_reminder_filter, build_crm_dashboard
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/crm", tags=["crm"])


def not_found_response() -> JSONResponse:
    return JSONResponse(status_code=404, content=error_response("customer not found"))


def validation_error_response(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_response(message))


@router.get("/dashboard")
def crm_dashboard(db: Session = Depends(get_db)):
    return success_response(build_crm_dashboard(db))


@router.get("/customers")
def list_customers(
    source_type: str | None = None,
    source_channel: str | None = None,
    platform: str | None = None,
    lead_level: str | None = None,
    status: str | None = None,
    owner_name: str | None = None,
    keyword: str | None = None,
    reminder: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(CrmCustomer)
    if source_type:
        query = query.filter(CrmCustomer.source_type == source_type)
    if source_channel:
        query = query.filter(CrmCustomer.source_channel == source_channel)
    if platform:
        query = query.filter(CrmCustomer.platform == platform)
    if lead_level:
        query = query.filter(CrmCustomer.lead_level == lead_level)
    if status:
        query = query.filter(CrmCustomer.status == status)
    if owner_name:
        query = query.filter(CrmCustomer.owner_name == owner_name)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            (CrmCustomer.customer_name.ilike(pattern)) | (CrmCustomer.nickname.ilike(pattern)) | (CrmCustomer.phone.ilike(pattern))
        )
    if reminder:
        query = apply_reminder_filter(query, reminder)
    query = query.order_by(CrmCustomer.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return success_response({
        "items": [CrmCustomerOut.model_validate(c).model_dump(mode="json") for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/customers")
def create_customer_manual(payload: CrmCustomerManualCreate, db: Session = Depends(get_db)):
    customer = CrmCustomer(
        source_type="manual",
        customer_name=payload.customer_name,
        nickname=payload.nickname,
        phone=payload.phone,
        wechat=payload.wechat,
        source_channel=payload.source_channel,
        demand_type=payload.demand_type,
        demand_description=payload.demand_description,
        intended_amount=payload.intended_amount,
        city=payload.city,
        lead_level=payload.lead_level,
        status="pending",
        owner_name=payload.owner_name or "未分配",
        entered_by=payload.entered_by,
        notes=payload.notes,
        next_follow_up_at=payload.next_follow_up_at,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return success_response(CrmCustomerOut.model_validate(customer).model_dump(mode="json"))


@router.post("/customers/from-lead/{lead_id}")
def create_customer_from_lead(lead_id: int, db: Session = Depends(get_db)):
    from app.models.lead import Lead
    from app.services.crm_service import convert_lead_to_crm

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead is None:
        return JSONResponse(status_code=404, content=error_response("lead not found"))

    try:
        customer = convert_lead_to_crm(db=db, lead=lead)
    except ValueError as exc:
        return validation_error_response(str(exc))

    return success_response(CrmCustomerOut.model_validate(customer).model_dump(mode="json"))


@router.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if customer is None:
        return not_found_response()
    return success_response(CrmCustomerOut.model_validate(customer).model_dump(mode="json"))


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: int, payload: CrmCustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if customer is None:
        return not_found_response()
    if payload.status is not None and payload.status not in CRM_CUSTOMER_STATUSES:
        return validation_error_response(f"invalid status: {payload.status}, must be one of: {', '.join(CRM_CUSTOMER_STATUSES)}")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    if payload.status == "converted" and customer.converted_at is None:
        customer.converted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(customer)
    return success_response(CrmCustomerOut.model_validate(customer).model_dump(mode="json"))


@router.post("/customers/{customer_id}/follow-records")
def create_follow_record(customer_id: int, payload: CrmFollowRecordCreate, db: Session = Depends(get_db)):
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if customer is None:
        return not_found_response()
    record = CrmFollowRecord(
        customer_id=customer_id,
        follow_type=payload.follow_type,
        content=payload.content,
        next_follow_up_at=payload.next_follow_up_at,
    )
    db.add(record)
    now = datetime.now(timezone.utc)
    customer.last_follow_up_at = now
    if payload.next_follow_up_at:
        customer.next_follow_up_at = payload.next_follow_up_at
    db.commit()
    db.refresh(record)
    return success_response(CrmFollowRecordOut.model_validate(record).model_dump(mode="json"))


@router.get("/customers/{customer_id}/follow-records")
def list_follow_records(
    customer_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if customer is None:
        return not_found_response()
    query = db.query(CrmFollowRecord).filter(CrmFollowRecord.customer_id == customer_id)
    query = query.order_by(CrmFollowRecord.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return success_response({
        "items": [CrmFollowRecordOut.model_validate(r).model_dump(mode="json") for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })
