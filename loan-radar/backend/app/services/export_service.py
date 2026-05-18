import csv
import io

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.lead import Lead

VALID_LEAD_STATUSES = {"new", "contacted", "interested", "invalid", "converted"}

LEAD_STATUS_LABELS = {
    "new": "新线索",
    "contacted": "已跟进",
    "interested": "有意向",
    "invalid": "无效",
    "converted": "已转化",
}


def build_leads_query(
    db: Session,
    lead_level: str | None = None,
    demand_type: str | None = None,
    risk_level: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
    source_post_id: int | None = None,
    source_comment_id: int | None = None,
    is_duplicate: bool | None = None,
    converted_to_crm: bool | None = None,
    created_after: str | None = None,
):
    query = db.query(Lead)

    if lead_level is not None:
        query = query.filter(Lead.lead_level == lead_level)
    if demand_type is not None:
        query = query.filter(Lead.demand_type == demand_type)
    if risk_level is not None:
        query = query.filter(Lead.risk_level == risk_level)
    if platform is not None:
        query = query.filter(Lead.platform == platform)
    if status is not None:
        query = query.filter(Lead.status == status)
    if source_type is not None:
        query = query.filter(Lead.source_type == source_type)
    if source_post_id is not None:
        query = query.filter(Lead.source_post_id == source_post_id)
    if source_comment_id is not None:
        query = query.filter(Lead.source_comment_id == source_comment_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Lead.content.ilike(pattern),
                Lead.user_name.ilike(pattern),
                Lead.reason.ilike(pattern),
            )
        )
    if is_duplicate is not None:
        query = query.filter(Lead.is_duplicate == is_duplicate)
    if converted_to_crm is not None:
        if converted_to_crm:
            query = query.filter(Lead.crm_customer_id.isnot(None))
        else:
            query = query.filter(Lead.crm_customer_id.is_(None))
    if created_after:
        try:
            after_dt = datetime.fromisoformat(created_after)
            if after_dt.tzinfo is None:
                after_dt = after_dt.replace(tzinfo=timezone.utc)
            query = query.filter(Lead.created_at >= after_dt)
        except (ValueError, TypeError):
            pass

    return query


def export_leads_csv(leads: list[Lead]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "线索等级",
            "评分",
            "需求类型",
            "评论内容",
            "识别理由",
            "跟进话术",
            "风险提示",
            "来源平台",
            "状态",
            "备注",
            "是否重复",
            "重复原因",
            "重复组ID",
            "创建时间",
        ]
    )

    for lead in leads:
        writer.writerow(
            [
                lead.lead_level,
                lead.lead_score,
                lead.demand_type or "",
                lead.content or "",
                lead.reason or "",
                lead.follow_up_script or "",
                lead.risk_level or "",
                lead.platform,
                LEAD_STATUS_LABELS.get(lead.status, lead.status),
                lead.notes or "",
                "是" if lead.is_duplicate else "否",
                lead.duplicate_reason or "",
                lead.duplicate_group_id or "",
                lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else "",
            ]
        )

    return "\ufeff".encode("utf-8") + output.getvalue().encode("utf-8")
