from typing import Annotated, Any, Type

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.models.crm import (
    CrmContract,
    CrmCustomer,
    CrmFollowUpRecord,
    CrmOpportunity,
    CrmProduct,
    CrmReceivable,
    CrmReceivablePlan,
    CrmTask,
)
from app.schemas.crm import (
    CrmContractCreate,
    CrmCustomerCreate,
    CrmCustomerUpdate,
    CrmFollowUpCreate,
    CrmOpportunityCreate,
    CrmOpportunityUpdate,
    CrmProductCreate,
    CrmReceivableCreate,
    CrmReceivablePlanCreate,
    CrmTaskCreate,
    CrmTaskUpdate,
)
from app.services.crm_service import (
    CRM_STAGES,
    CUSTOMER_STATUSES,
    TASK_STATUSES,
    build_crm_dashboard,
    contract_to_dict,
    customer_to_dict,
    follow_up_to_dict,
    opportunity_to_dict,
    receivable_plan_to_dict,
    receivable_to_dict,
    task_to_dict,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/crm", tags=["crm"])


def validation_error(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_response(message))


def not_found(name: str) -> JSONResponse:
    return JSONResponse(status_code=404, content=error_response(f"{name} not found"))


def _page_response(query, page: int, page_size: int, mapper):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return success_response(
        {
            "items": [mapper(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


def _create_model(db: Session, model: Type, payload: BaseModel):
    obj = model(**payload.model_dump(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _update_model(db: Session, obj: Any, payload: BaseModel):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/dashboard")
def crm_dashboard(db: Session = Depends(get_db)):
    return success_response(build_crm_dashboard(db))


@router.get("/customers")
def list_customers(
    owner_name: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(CrmCustomer)
    if owner_name:
        query = query.filter(CrmCustomer.owner_name == owner_name)
    if status:
        query = query.filter(CrmCustomer.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(CrmCustomer.name.ilike(pattern))
    query = query.order_by(CrmCustomer.id.desc())
    return _page_response(query, page, page_size, customer_to_dict)


@router.post("/customers")
def create_customer(payload: CrmCustomerCreate, db: Session = Depends(get_db)):
    if payload.status not in CUSTOMER_STATUSES:
        return validation_error(f"invalid customer status: {payload.status}")
    customer = _create_model(db, CrmCustomer, payload)
    return success_response(customer_to_dict(customer))


@router.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if customer is None:
        return not_found("customer")
    return success_response(customer_to_dict(customer))


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: int, payload: CrmCustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    if customer is None:
        return not_found("customer")
    if payload.status is not None and payload.status not in CUSTOMER_STATUSES:
        return validation_error(f"invalid customer status: {payload.status}")
    customer = _update_model(db, customer, payload)
    return success_response(customer_to_dict(customer))


@router.get("/opportunities")
def list_opportunities(
    owner_name: str | None = None,
    stage: str | None = None,
    customer_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(CrmOpportunity)
    if owner_name:
        query = query.filter(CrmOpportunity.owner_name == owner_name)
    if stage:
        query = query.filter(CrmOpportunity.stage == stage)
    if customer_id is not None:
        query = query.filter(CrmOpportunity.customer_id == customer_id)
    query = query.order_by(CrmOpportunity.id.desc())
    return _page_response(query, page, page_size, lambda item: opportunity_to_dict(item, db))


@router.post("/opportunities")
def create_opportunity(payload: CrmOpportunityCreate, db: Session = Depends(get_db)):
    if payload.stage not in CRM_STAGES:
        return validation_error(f"invalid opportunity stage: {payload.stage}")
    opportunity = _create_model(db, CrmOpportunity, payload)
    return success_response(opportunity_to_dict(opportunity, db))


@router.patch("/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: int,
    payload: CrmOpportunityUpdate,
    db: Session = Depends(get_db),
):
    opportunity = db.query(CrmOpportunity).filter(CrmOpportunity.id == opportunity_id).first()
    if opportunity is None:
        return not_found("opportunity")
    if payload.stage is not None and payload.stage not in CRM_STAGES:
        return validation_error(f"invalid opportunity stage: {payload.stage}")
    before_stage = opportunity.stage
    opportunity = _update_model(db, opportunity, payload)
    if payload.stage is not None and payload.stage != before_stage:
        db.add(
            CrmFollowUpRecord(
                customer_id=opportunity.customer_id,
                opportunity_id=opportunity.id,
                owner_name=opportunity.owner_name,
                follow_up_type="stage_change",
                content=f"销售阶段从 {before_stage} 更新为 {payload.stage}",
                stage_before=before_stage,
                stage_after=payload.stage,
            )
        )
        db.commit()
    return success_response(opportunity_to_dict(opportunity, db))


@router.get("/follow-ups")
def list_follow_ups(
    customer_id: int | None = None,
    opportunity_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(CrmFollowUpRecord)
    if customer_id is not None:
        query = query.filter(CrmFollowUpRecord.customer_id == customer_id)
    if opportunity_id is not None:
        query = query.filter(CrmFollowUpRecord.opportunity_id == opportunity_id)
    query = query.order_by(CrmFollowUpRecord.id.desc())
    return _page_response(query, page, page_size, lambda item: follow_up_to_dict(item, db))


@router.post("/follow-ups")
def create_follow_up(payload: CrmFollowUpCreate, db: Session = Depends(get_db)):
    record = _create_model(db, CrmFollowUpRecord, payload)
    if payload.stage_after and payload.opportunity_id:
        opportunity = db.query(CrmOpportunity).filter(CrmOpportunity.id == payload.opportunity_id).first()
        if opportunity and payload.stage_after in CRM_STAGES:
            opportunity.stage = payload.stage_after
            db.commit()
    return success_response(follow_up_to_dict(record, db))


@router.get("/tasks")
def list_tasks(
    owner_name: str | None = None,
    status: str | None = None,
    customer_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(CrmTask)
    if owner_name:
        query = query.filter(CrmTask.owner_name == owner_name)
    if status:
        query = query.filter(CrmTask.status == status)
    if customer_id is not None:
        query = query.filter(CrmTask.customer_id == customer_id)
    query = query.order_by(CrmTask.due_at.asc().nullslast(), CrmTask.id.desc())
    return _page_response(query, page, page_size, lambda item: task_to_dict(item, db))


@router.post("/tasks")
def create_task(payload: CrmTaskCreate, db: Session = Depends(get_db)):
    if payload.status not in TASK_STATUSES:
        return validation_error(f"invalid task status: {payload.status}")
    task = _create_model(db, CrmTask, payload)
    return success_response(task_to_dict(task, db))


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: CrmTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(CrmTask).filter(CrmTask.id == task_id).first()
    if task is None:
        return not_found("task")
    if payload.status is not None and payload.status not in TASK_STATUSES:
        return validation_error(f"invalid task status: {payload.status}")
    task = _update_model(db, task, payload)
    return success_response(task_to_dict(task, db))


@router.post("/products")
def create_product(payload: CrmProductCreate, db: Session = Depends(get_db)):
    product = _create_model(db, CrmProduct, payload)
    return success_response(_model_dict(product))


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    products = db.query(CrmProduct).order_by(CrmProduct.id.desc()).all()
    return success_response([_model_dict(product) for product in products])


@router.get("/contracts")
def list_contracts(
    customer_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(CrmContract)
    if customer_id is not None:
        query = query.filter(CrmContract.customer_id == customer_id)
    if status:
        query = query.filter(CrmContract.status == status)
    contracts = query.order_by(CrmContract.id.desc()).all()
    return success_response([contract_to_dict(contract, db) for contract in contracts])


@router.post("/contracts")
def create_contract(payload: CrmContractCreate, db: Session = Depends(get_db)):
    contract = _create_model(db, CrmContract, payload)
    return success_response(contract_to_dict(contract, db))


@router.get("/receivable-plans")
def list_receivable_plans(
    customer_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(CrmReceivablePlan)
    if customer_id is not None:
        query = query.filter(CrmReceivablePlan.customer_id == customer_id)
    if status:
        query = query.filter(CrmReceivablePlan.status == status)
    plans = query.order_by(CrmReceivablePlan.due_date.asc()).all()
    return success_response([receivable_plan_to_dict(plan, db) for plan in plans])


@router.post("/receivable-plans")
def create_receivable_plan(payload: CrmReceivablePlanCreate, db: Session = Depends(get_db)):
    plan = _create_model(db, CrmReceivablePlan, payload)
    return success_response(receivable_plan_to_dict(plan, db))


@router.get("/receivables")
def list_receivables(customer_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(CrmReceivable)
    if customer_id is not None:
        query = query.filter(CrmReceivable.customer_id == customer_id)
    receivables = query.order_by(CrmReceivable.received_at.desc()).all()
    return success_response([receivable_to_dict(receivable, db) for receivable in receivables])


@router.post("/receivables")
def create_receivable(payload: CrmReceivableCreate, db: Session = Depends(get_db)):
    receivable = _create_model(db, CrmReceivable, payload)
    if payload.receivable_plan_id:
        plan = db.query(CrmReceivablePlan).filter(CrmReceivablePlan.id == payload.receivable_plan_id).first()
        if plan:
            plan.received_amount = (plan.received_amount or 0) + payload.amount
            if plan.received_amount >= plan.amount:
                plan.status = "received"
            db.commit()
    return success_response(receivable_to_dict(receivable, db))


def _model_dict(model: Any) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}
