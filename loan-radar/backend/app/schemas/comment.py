from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    post_id: str
    comment_id: str
    user_name: str | None = None
    user_profile_url: str | None = None
    content: str | None = None
    like_count: int
    publish_time: datetime | None = None
    is_suspected_demand: bool
    demand_type: str | None = None
    risk_level: str | None = None
    raw_data: Any | None = None
    created_at: datetime
    updated_at: datetime
