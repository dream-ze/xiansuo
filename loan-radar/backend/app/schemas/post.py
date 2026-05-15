from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    source_id: int
    source_type: str
    post_id: str
    title: str | None = None
    content: str | None = None
    post_url: str | None = None
    author_name: str | None = None
    author_profile_url: str | None = None
    like_count: int
    comment_count: int
    collect_count: int
    publish_time: datetime | None = None
    is_hot: bool
    lead_count: int = 0
    raw_data: Any | None = None
    created_at: datetime
    updated_at: datetime
