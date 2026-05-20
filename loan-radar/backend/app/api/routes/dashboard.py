from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.core.deps import require_current_user
from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.crm import CrmCustomer
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.note import Note
from app.models.pending_competitor import PendingCompetitorAccount
from app.models.post import Post
from app.utils.response import success_response

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(require_current_user)])


def _count_today(db: Session, model, today):
    return db.query(func.count(model.id)).filter(
        func.date(model.created_at) == today
    ).scalar() or 0


def _count_total(db: Session, model, extra_filters=None):
    q = db.query(func.count(model.id))
    if extra_filters:
        for f in extra_filters:
            q = q.filter(f)
    return q.scalar() or 0


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    source_count = db.query(func.count(MonitorSource.id)).filter(
        MonitorSource.enabled == True
    ).scalar() or 0

    today_task_count = _count_today(db, CrawlTask, today)
    today_post_count = _count_today(db, Post, today)
    today_comment_count = _count_today(db, Comment, today)
    today_lead_count = _count_today(db, Lead, today)
    today_a_lead_count = db.query(func.count(Lead.id)).filter(
        func.date(Lead.created_at) == today,
        Lead.lead_level == "A",
    ).scalar() or 0

    total_task_count = _count_total(db, CrawlTask)
    total_post_count = _count_total(db, Post)
    total_comment_count = _count_total(db, Comment)
    total_lead_count = _count_total(db, Lead)
    total_a_lead_count = _count_total(db, Lead, [Lead.lead_level == "A"])

    yesterday_lead_count = db.query(func.count(Lead.id)).filter(
        func.date(Lead.created_at) == yesterday,
    ).scalar() or 0
    yesterday_a_lead_count = db.query(func.count(Lead.id)).filter(
        func.date(Lead.created_at) == yesterday,
        Lead.lead_level == "A",
    ).scalar() or 0
    yesterday_post_count = _count_today(db, Post, yesterday)

    pending_competitor_count = db.query(func.count(PendingCompetitorAccount.id)).filter(
        PendingCompetitorAccount.status == "pending",
    ).scalar() or 0

    crm_today_new = db.query(func.count(CrmCustomer.id)).filter(
        func.date(CrmCustomer.created_at) == today,
    ).scalar() or 0
    crm_pending_follow = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "pending",
    ).scalar() or 0
    crm_overdue_follow = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.next_follow_up_at.isnot(None),
        CrmCustomer.next_follow_up_at < datetime.now(timezone.utc),
        CrmCustomer.status.notin_(["converted", "invalid"]),
    ).scalar() or 0
    crm_converted = db.query(func.count(CrmCustomer.id)).filter(
        CrmCustomer.status == "converted",
    ).scalar() or 0

    xhs_notes_count = db.query(func.count(Note.id)).scalar() or 0
    xhs_notes_today = _count_today(db, Note, today)
    xhs_notes_with_video = db.query(func.count(Note.id)).filter(
        Note.note_id != None,
    ).scalar() or 0

    recent_a_leads = (
        db.query(Lead)
        .filter(Lead.lead_level == "A")
        .order_by(Lead.created_at.desc())
        .limit(5)
        .all()
    )

    recent_tasks = (
        db.query(CrawlTask)
        .order_by(CrawlTask.created_at.desc())
        .limit(5)
        .all()
    )

    a_leads_data = []
    for lead in recent_a_leads:
        a_leads_data.append({
            "id": lead.id,
            "platform": lead.platform,
            "user_name": lead.user_name or "",
            "content": (lead.content or "")[:100],
            "lead_score": lead.lead_score,
            "demand_type": lead.demand_type or "",
            "follow_up_script": lead.follow_up_script or "",
            "created_at": lead.created_at.isoformat() if lead.created_at else "",
        })

    tasks_data = []
    for task in recent_tasks:
        tasks_data.append({
            "id": task.id,
            "source_type": task.source_type,
            "source_value": task.source_value or "",
            "platform": task.platform,
            "status": task.status,
            "post_count": task.post_count,
            "comment_count": task.comment_count,
            "lead_count": task.lead_count,
            "error_message": task.error_message or "",
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else "",
        })

    return success_response({
        "source_count": source_count,
        "today_task_count": today_task_count,
        "today_post_count": today_post_count,
        "today_comment_count": today_comment_count,
        "today_lead_count": today_lead_count,
        "today_a_lead_count": today_a_lead_count,
        "total_task_count": total_task_count,
        "total_post_count": total_post_count,
        "total_comment_count": total_comment_count,
        "total_lead_count": total_lead_count,
        "total_a_lead_count": total_a_lead_count,
        "yesterday_lead_count": yesterday_lead_count,
        "yesterday_a_lead_count": yesterday_a_lead_count,
        "yesterday_post_count": yesterday_post_count,
        "pending_competitor_count": pending_competitor_count,
        "crm_today_new": crm_today_new,
        "crm_pending_follow": crm_pending_follow,
        "crm_overdue_follow": crm_overdue_follow,
        "crm_converted": crm_converted,
        "xhs_notes_count": xhs_notes_count,
        "xhs_notes_today": xhs_notes_today,
        "recent_a_leads": a_leads_data,
        "recent_tasks": tasks_data,
    })


@router.get("/media-crawler-health")
def get_media_crawler_health():
    import os
    from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS, PLATFORM_LABELS

    mc_home = os.getenv("MEDIA_CRAWLER_HOME")
    embedded_mode = bool(mc_home)

    shared_db_info = None
    try:
        from app.collectors.media_crawler.shared_db_reader import is_shared_db_available, _get_raw_db_path
        if is_shared_db_available():
            shared_db_info = {"available": True, "path": _get_raw_db_path()}
        else:
            shared_db_info = {"available": False}
    except Exception:
        shared_db_info = {"available": False}

    if embedded_mode:
        from pathlib import Path
        home_path = Path(mc_home) if mc_home else None
        mc_available = home_path.is_dir() if home_path else False
        return success_response({
            "status": "healthy" if mc_available else "misconfigured",
            "mode": "embedded",
            "media_crawler_home": mc_home,
            "shared_db": shared_db_info,
            "supported_platforms": [
                {"value": p, "label": PLATFORM_LABELS.get(p, p)}
                for p in sorted(SUPPORTED_PLATFORMS)
            ],
        })

    from app.collectors.media_crawler.bridge import MediaCrawlerBridge
    bridge = MediaCrawlerBridge()
    is_healthy = bridge.health_check()

    return success_response({
        "status": "healthy" if is_healthy else "unreachable",
        "mode": "http_bridge",
        "api_base_url": bridge.api_base_url,
        "shared_db": shared_db_info,
        "supported_platforms": [
            {"value": p, "label": PLATFORM_LABELS.get(p, p)}
            for p in sorted(SUPPORTED_PLATFORMS)
        ],
    })
