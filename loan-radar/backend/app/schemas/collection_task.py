from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CollectionTaskCreate(BaseModel):
    platform: str = "xhs"
    source_type: Literal["keyword", "account", "post_url"]
    source_value: str = Field(min_length=1, max_length=1000)
    limit_count: int = Field(default=10, ge=1, le=100)


class CollectionTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    source_type: str
    source_value: str
    status: str
    limit_count: int
    collected_posts: int
    collected_comments: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime