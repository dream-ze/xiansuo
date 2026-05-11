import csv
import io

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.lead import Lead

VALID_LEAD_STATUSES = {"new", "contacted", "invalid", "converted"}


def build_leads_query(
    db: Session,
    lead_level: str | None = None,
    demand_type: str | None = None,
    risk_level: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
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
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Lead.content.ilike(pattern),
                Lead.user_name.ilike(pattern),
                Lead.reason.ilike(pattern),
            )
        )

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
                lead.status,
                lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else "",
            ]
        )

    # UTF-8 BOM，避免 Excel 中文乱码
    return "\ufeff".encode("utf-8") + output.getvalue().encode("utf-8")
