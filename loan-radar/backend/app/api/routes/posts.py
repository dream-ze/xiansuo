from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.models.lead import Lead
from app.models.post import Post
from app.schemas.post import PostOut
from app.utils.response import error_response, success_response

router = APIRouter(tags=["posts"])


def _enrich_post_out(post: Post, db: Session) -> dict:
    data = PostOut.model_validate(post).model_dump(mode="json")
    lead_count = db.query(func.count(Lead.id)).filter(
        Lead.source_post_id == post.id
    ).scalar()
    data["lead_count"] = lead_count or 0
    return data


@router.get("/api/posts/{post_id}")
def get_post_endpoint(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return error_response("post not found")
    data = _enrich_post_out(post, db)
    return success_response(data)


@router.get("/api/posts")
def list_posts_endpoint(
    platform: str | None = None,
    source_type: str | None = None,
    source_id: int | None = None,
    is_hot: bool | None = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Post)

    if platform is not None:
        query = query.filter(Post.platform == platform)
    if source_type is not None:
        query = query.filter(Post.source_type == source_type)
    if source_id is not None:
        query = query.filter(Post.source_id == source_id)
    if is_hot is not None:
        query = query.filter(Post.is_hot == is_hot)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern),
                Post.post_id.ilike(pattern),
                Post.author_name.ilike(pattern),
            )
        )

    total = query.count()
    posts = (
        query.order_by(Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_enrich_post_out(post, db) for post in posts]
    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
