from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.routes.monitor_sources import get_db
from app.models.post import Post
from app.schemas.post import PostOut
from app.utils.response import success_response

router = APIRouter(tags=["posts"])


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

    items = [PostOut.model_validate(post).model_dump(mode="json") for post in posts]
    return success_response(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
