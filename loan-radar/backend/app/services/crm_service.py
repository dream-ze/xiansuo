import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crm import (
    CrmContract,
    CrmCustomer,
    CrmFollowUpRecord,
    CrmOpportunity,
    CrmReceivable,
    CrmReceivablePlan,
    CrmTask,
)
from app.models.lead import Lead

CRM_STAGES = {
    "new_customer",
    "contacted",
    "demand_confirmed",
    "qualification_review",
    "proposal_sent",
    "contract_signed",
    "funded_won",
    "lost",
}

TASK_STATUSES = {"pending", "done", "canceled"}
CUSTOMER_STATUSES = {"new", "following", "qualified", "deal", "lost", "invalid"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_overdue(due_at: datetime | None, status: str) -> bool:
    if due_at is None or status != "pending":
        return False
    return due_at < now_utc()


def receivable_plan_is_overdue(due_date: datetime, status: str) -> bool:
    return status == "pending" and due_date < now_utc()


def infer_amount(lead: Lead) -> float | None:
    evidence = lead.evidence if isinstance(lead.evidence, dict) else {}
    candidates: list[str] = []
    amounts = evidence.get("amounts")
    if isinstance(amounts, list):
        candidates.extend(str(item) for item in amounts)
    if lead.content:
        candidates.append(lead.content)

    for candidate in candidates:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(万|w|W)", candidate)
        if match:
            return float(match.group(1)) * 10000
        match = re.search(r"(\d+(?:\.\d+)?)\s*(千|k|K)", candidate)
        if match:
            return float(match.group(1)) * 1000
        match = re.search(r"(\d{4,})", candidate)
        if match:
            return float(match.group(1))
    return None


def _dump(model: Any, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data = {column.name: getattr(model, column.name) for column in model.__table__.columns}
    if extra:
        data.update(extra)
    return data


def _customer_name_for(db: Session, customer_id: int | None) -> str | None:
    if customer_id is None:
        return None
    customer = db.query(CrmCustomer).filter(CrmCustomer.id == customer_id).first()
    return customer.name if customer else None


def _opportunity_name_for(db: Session, opportunity_id: int | None) -> str | None:
    if opportunity_id is None:
        return None
    opportunity = db.query(CrmOpportunity).filter(CrmOpportunity.id == opportunity_id).first()
    return opportunity.name if opportunity else None


def task_to_dict(task: CrmTask, db: Session) -> dict[str, Any]:
    return _dump(
        task,
        {
            "customer_name": _customer_name_for(db, task.customer_id),
            "opportunity_name": _opportunity_name_for(db, task.opportunity_id),
            "is_overdue": is_overdue(task.due_at, task.status),
        },
    )


def receivable_plan_to_dict(plan: CrmReceivablePlan, db: Session) -> dict[str, Any]:
    contract = db.query(CrmContract).filter(CrmContract.id == plan.contract_id).first()
    return _dump(
        plan,
        {
            "customer_name": _customer_name_for(db, plan.customer_id),
            "contract_title": contract.title if contract else None,
            "is_overdue": receivable_plan_is_overdue(plan.due_date, plan.status),
        },
    )


def opportunity_to_dict(opportunity: CrmOpportunity, db: Session) -> dict[str, Any]:
    return _dump(opportunity, {"customer_name": _customer_name_for(db, opportunity.customer_id)})


def customer_to_dict(customer: CrmCustomer) -> dict[str, Any]:
    return _dump(customer)


def follow_up_to_dict(record: CrmFollowUpRecord, db: Session) -> dict[str, Any]:
    return _dump(
        record,
        {
            "customer_name": _customer_name_for(db, record.customer_id),
            "opportunity_name": _opportunity_name_for(db, record.opportunity_id),
        },
    )


def contract_to_dict(contract: CrmContract, db: Session) -> dict[str, Any]:
    return _dump(contract, {"customer_name": _customer_name_for(db, contract.customer_id)})


def receivable_to_dict(receivable: CrmReceivable, db: Session) -> dict[str, Any]:
    contract = db.query(CrmContract).filter(CrmContract.id == receivable.contract_id).first()
    return _dump(
        receivable,
        {
            "customer_name": _customer_name_for(db, receivable.customer_id),
            "contract_title": contract.title if contract else None,
        },
    )


def convert_lead_to_crm(
    db: Session,
    lead: Lead,
    owner_name: str | None = None,
    next_follow_up_at: datetime | None = None,
) -> tuple[CrmCustomer, CrmOpportunity, CrmTask]:
    if lead.crm_customer_id or lead.converted_to_crm_at:
        raise ValueError("lead already converted to CRM")

    existing = db.query(CrmCustomer).filter(CrmCustomer.source_lead_id == lead.id).first()
    if existing is not None:
        raise ValueError("lead already converted to CRM")

    amount = infer_amount(lead)
    owner = owner_name or "未分配"
    customer = CrmCustomer(
        name=lead.user_name or f"线索 #{lead.id}",
        contact_info=lead.user_profile_url,
        owner_name=owner,
        source_lead_id=lead.id,
        source_platform=lead.platform,
        source_type=lead.source_type,
        source_post_id=lead.source_post_id,
        source_comment_id=lead.source_comment_id,
        source_summary=lead.content,
        demand_amount=amount,
        loan_purpose=lead.demand_type,
        qualification_summary=lead.reason,
        risk_level=lead.risk_level,
        customer_level=lead.lead_level,
        status="new",
        evidence=lead.evidence,
        notes=lead.notes,
    )
    db.add(customer)
    db.flush()

    opportunity = CrmOpportunity(
        customer_id=customer.id,
        source_lead_id=lead.id,
        name=f"{customer.name} - {lead.demand_type or '贷款商机'}",
        owner_name=owner,
        stage="new_customer",
        estimated_amount=amount,
        probability=20 if lead.lead_level == "A" else 10,
        next_step=lead.follow_up_script or "确认客户贷款用途、金额、资质和时间要求。",
    )
    db.add(opportunity)
    db.flush()

    due_at = next_follow_up_at or (now_utc() + timedelta(days=1))
    task = CrmTask(
        customer_id=customer.id,
        opportunity_id=opportunity.id,
        title=f"首跟进：{customer.name}",
        task_type="follow_up",
        owner_name=owner,
        due_at=due_at,
        status="pending",
        priority="high" if lead.lead_level == "A" else "normal",
        suggestion=lead.follow_up_script or "先确认用途、金额、收入、征信和可接受方案。",
    )
    db.add(task)

    lead.crm_customer_id = customer.id
    lead.crm_opportunity_id = opportunity.id
    lead.converted_to_crm_at = now_utc()
    lead.status = "contacted" if lead.status == "new" else lead.status

    db.commit()
    db.refresh(customer)
    db.refresh(opportunity)
    db.refresh(task)
    db.refresh(lead)
    return customer, opportunity, task


def build_crm_dashboard(db: Session) -> dict[str, Any]:
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    converted_leads = db.query(func.count(Lead.id)).filter(Lead.crm_customer_id.isnot(None)).scalar() or 0
    customer_count = db.query(func.count(CrmCustomer.id)).scalar() or 0
    opportunity_count = db.query(func.count(CrmOpportunity.id)).scalar() or 0
    won_count = db.query(func.count(CrmOpportunity.id)).filter(CrmOpportunity.stage == "funded_won").scalar() or 0
    lost_count = db.query(func.count(CrmOpportunity.id)).filter(CrmOpportunity.stage == "lost").scalar() or 0
    pending_task_count = db.query(func.count(CrmTask.id)).filter(CrmTask.status == "pending").scalar() or 0

    tasks = db.query(CrmTask).filter(CrmTask.status == "pending").all()
    overdue_task_count = sum(1 for task in tasks if is_overdue(task.due_at, task.status))

    plans = db.query(CrmReceivablePlan).filter(CrmReceivablePlan.status == "pending").all()
    overdue_receivable_count = sum(
        1 for plan in plans if receivable_plan_is_overdue(plan.due_date, plan.status)
    )
    upcoming_receivable_count = sum(
        1
        for plan in plans
        if not receivable_plan_is_overdue(plan.due_date, plan.status)
        and plan.due_date <= now_utc() + timedelta(days=7)
    )

    stage_rows = (
        db.query(CrmOpportunity.stage, func.count(CrmOpportunity.id))
        .group_by(CrmOpportunity.stage)
        .all()
    )
    source_rows = (
        db.query(CrmCustomer.source_platform, func.count(CrmCustomer.id))
        .group_by(CrmCustomer.source_platform)
        .all()
    )

    return {
        "total_leads": total_leads,
        "converted_leads": converted_leads,
        "conversion_rate": round(converted_leads * 100 / total_leads, 2) if total_leads else 0,
        "customer_count": customer_count,
        "opportunity_count": opportunity_count,
        "won_count": won_count,
        "lost_count": lost_count,
        "win_rate": round(won_count * 100 / opportunity_count, 2) if opportunity_count else 0,
        "pending_task_count": pending_task_count,
        "overdue_task_count": overdue_task_count,
        "upcoming_receivable_count": upcoming_receivable_count,
        "overdue_receivable_count": overdue_receivable_count,
        "stage_counts": {stage: count for stage, count in stage_rows},
        "source_counts": {(platform or "unknown"): count for platform, count in source_rows},
    }
