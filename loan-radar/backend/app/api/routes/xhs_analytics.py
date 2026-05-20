from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_current_user
from app.models import Note, PlatformAccount, User
from app.schemas.common import paginated

router = APIRouter(prefix="/api/xhs/analytics", tags=["xhs-analytics"])


@router.get("/overview")
def analytics_overview(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id
    saved_notes = db.scalar(select(func.count()).where(Note.user_id == user_id)) or 0
    comment_count = 0
    healthy_accounts = db.scalar(
        select(func.count()).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform == "xhs",
            PlatformAccount.status == "valid",
        )
    ) or 0
    at_risk_accounts = db.scalar(
        select(func.count()).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform == "xhs",
            PlatformAccount.status != "valid",
        )
    ) or 0
    return {
        "platform": "xhs",
        "today_crawls": 0,
        "saved_notes": saved_notes,
        "pending_publishes": 0,
        "healthy_accounts": healthy_accounts,
        "at_risk_accounts": at_risk_accounts,
        "comment_count": comment_count,
        "total_engagement": 0,
        "hot_topics": [],
        "recent_activity": [],
    }


@router.get("/top-content")
def analytics_top_content(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {"items": []}


@router.get("/hot-topics")
def analytics_hot_topics(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {"items": []}


@router.get("/comment-insights")
def analytics_comment_insights(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {
        "total_comments": 0,
        "question_count": 0,
        "top_terms": [],
        "top_comments": [],
    }


@router.get("/benchmarks")
def analytics_benchmarks(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {"targets": [], "summary": {}}


@router.post("/benchmarks/{target_id}/create-drafts")
def benchmark_create_drafts(
    target_id: int,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {"created_count": 0, "draft_ids": []}


@router.post("/reports")
def analytics_reports(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return {"items": []}
