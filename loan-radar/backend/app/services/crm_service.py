from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.crm import CrmCustomer, CrmFollowRecord
from app.models.lead import Lead
from app.schemas.crm import CRM_CUSTOMER_STATUSES, CrmDashboardOut

EXCLUDED_REMINDER_STATUSES = ["converted", "invalid"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _reminder_base_filter(query):
    return query.filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.status.notin_(EXCLUDED_REMINDER_STATUSES),
    )


def apply_reminder_filter(query, reminder: str):
    now = now_utc()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    tomorrow_start = today_start + timedelta(days=1)
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

    weekday = today_start.weekday()
    week_start = today_start - timedelta(days=weekday)
    week_end = week_start + timedelta(days=6)
    week_end = week_end.replace(hour=23, minute=59, second=59)

    if reminder == "overdue":
        return _reminder_base_filter(query).filter(
            CrmCustomer.next_follow_up_at < now,
        )
    elif reminder == "today":
        return _reminder_base_filter(query).filter(
            CrmCustomer.next_follow_up_at >= today_start,
            CrmCustomer.next_follow_up_at <= today_end,
        )
    elif reminder == "tomorrow":
        return _reminder_base_filter(query).filter(
            CrmCustomer.next_follow_up_at >= tomorrow_start,
            CrmCustomer.next_follow_up_at <= tomorrow_end,
        )
    elif reminder == "this_week":
        return _reminder_base_filter(query).filter(
            CrmCustomer.next_follow_up_at >= week_start,
            CrmCustomer.next_follow_up_at <= week_end,
        )
    elif reminder == "none":
        return query.filter(
            CrmCustomer.next_follow_up_at.is_(None),
        )
    return query


def convert_lead_to_crm(
    db: Session,
    lead: Lead,
    owner_name: str | None = None,
    next_follow_up_at: datetime | None = None,
) -> CrmCustomer:
    if lead.crm_customer_id:
        raise ValueError("该线索已转入 CRM")

    existing = db.query(CrmCustomer).filter(
        CrmCustomer.lead_id == lead.id,
        CrmCustomer.source_type == "lead_conversion",
    ).first()
    if existing is not None:
        raise ValueError("该线索已转入 CRM")

    source_channel = None
    platform_map = {"xhs": "小红书", "douyin": "抖音", "zhihu": "知乎"}
    if lead.platform:
        source_channel = platform_map.get(lead.platform, lead.platform)

    customer = CrmCustomer(
        source_type="lead_conversion",
        lead_id=lead.id,
        platform=lead.platform,
        source_channel=source_channel,
        source_url=lead.user_profile_url,
        source_post_id=lead.source_post_id,
        nickname=lead.user_name,
        demand_type=lead.demand_type,
        lead_level=lead.lead_level,
        status="pending",
        owner_name=owner_name or "未分配",
        notes=lead.notes,
        next_follow_up_at=next_follow_up_at,
    )
    db.add(customer)
    db.flush()

    lead.crm_customer_id = customer.id
    lead.converted_to_crm_at = now_utc()
    if lead.status == "new":
        lead.status = "contacted"

    db.commit()
    db.refresh(customer)
    db.refresh(lead)
    return customer


def build_crm_dashboard(db: Session) -> dict[str, Any]:
    now = now_utc()
    today = now.date()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    tomorrow_start = today_start + timedelta(days=1)
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

    weekday = today_start.weekday()
    week_start = today_start - timedelta(days=weekday)
    week_end = week_start + timedelta(days=6)
    week_end = week_end.replace(hour=23, minute=59, second=59)

    total_customers = db.query(func.count(CrmCustomer.id)).scalar() or 0
    lead_conversion_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.source_type == "lead_conversion"
    ).scalar() or 0
    manual_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.source_type == "manual"
    ).scalar() or 0
    today_new = db.query(func.count(CrmCustomer.id)).filter(
        func.date(CrmCustomer.created_at) == today
    ).scalar() or 0
    today_manual = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.source_type == "manual",
        func.date(CrmCustomer.created_at) == today,
    ).scalar() or 0
    pending_follow = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "pending"
    ).scalar() or 0
    interested = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "interested"
    ).scalar() or 0
    converted = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "converted"
    ).scalar() or 0

    overdue_follow = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.next_follow_up_at < now,
        CrmCustomer.status.notin_(EXCLUDED_REMINDER_STATUSES),
    ).scalar() or 0

    today_follow_up_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.next_follow_up_at >= today_start,
        CrmCustomer.next_follow_up_at <= today_end,
        CrmCustomer.status.notin_(EXCLUDED_REMINDER_STATUSES),
    ).scalar() or 0

    tomorrow_follow_up_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.next_follow_up_at >= tomorrow_start,
        CrmCustomer.next_follow_up_at <= tomorrow_end,
        CrmCustomer.status.notin_(EXCLUDED_REMINDER_STATUSES),
    ).scalar() or 0

    this_week_follow_up_count = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.next_follow_up_at >= week_start,
        CrmCustomer.next_follow_up_at <= week_end,
        CrmCustomer.status.notin_(EXCLUDED_REMINDER_STATUSES),
    ).scalar() or 0

    status_rows = (
        db.query(CrmCustomer.status, func.count(CrmCustomer.id))
        .group_by(CrmCustomer.status)
        .all()
    )
    status_counts = {status: count for status, count in status_rows}

    level_rows = (
        db.query(CrmCustomer.lead_level, func.count(CrmCustomer.id))
        .group_by(CrmCustomer.lead_level)
        .all()
    )
    level_counts = {level or "unknown": count for level, count in level_rows}

    return CrmDashboardOut(
        total_customers=total_customers,
        lead_conversion_count=lead_conversion_count,
        manual_count=manual_count,
        today_new=today_new,
        today_manual=today_manual,
        pending_follow=pending_follow,
        interested=interested,
        converted=converted,
        overdue_follow=overdue_follow,
        today_follow_up_count=today_follow_up_count,
        tomorrow_follow_up_count=tomorrow_follow_up_count,
        this_week_follow_up_count=this_week_follow_up_count,
        status_counts=status_counts,
        level_counts=level_counts,
    ).model_dump()
