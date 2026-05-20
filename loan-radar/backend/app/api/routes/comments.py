from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.core.deps import require_current_user
from app.models.comment import Comment
from app.models.lead import Lead
from app.schemas.comment import CommentOut
from app.utils.response import success_response

router = APIRouter(tags=["comments"], dependencies=[Depends(require_current_user)])


def _enrich_comment_out(comment: Comment, db: Session) -> dict:
    data = CommentOut.model_validate(comment).model_dump(mode="json")
    has_lead = db.query(func.count(Lead.id)).filter(
        Lead.source_comment_id == comment.id
    ).scalar()
    data["has_lead"] = (has_lead or 0) > 0
    return data


@router.get("/api/comments")
def list_comments_endpoint(
    platform: str | None = None,
    demand_type: str | None = None,
    risk_level: str | None = None,
    is_suspected_demand: bool | None = None,
    post_id: str | None = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Comment)

    if platform is not None:
        query = query.filter(Comment.platform == platform)
    if demand_type is not None:
        query = query.filter(Comment.demand_type == demand_type)
    if risk_level is not None:
        query = query.filter(Comment.risk_level == risk_level)
    if is_suspected_demand is not None:
        query = query.filter(Comment.is_suspected_demand == is_suspected_demand)
    if post_id is not None:
        query = query.filter(Comment.post_id == post_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Comment.content.ilike(pattern),
                Comment.user_name.ilike(pattern),
                Comment.comment_id.ilike(pattern),
            )
        )

    total = query.count()
    comments = (
        query.order_by(Comment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_enrich_comment_out(comment, db) for comment in comments]
    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
