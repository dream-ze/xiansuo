from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CrawlTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int | None = None
    source_type: str
    source_value: str | None = None
    platform: str
    status: str
    progress: str | None = None
    limit_count: int
    retry_count: int = 0
    max_retries: int = 3
    last_error_type: str | None = None
    failure_type: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    post_count: int
    comment_count: int
    collected_posts: int
    collected_comments: int
    lead_count: int
    discovered_competitor_count: int
    duplicate_post_count: int = 0
    duplicate_comment_count: int = 0
    created_at: datetime
    updated_at: datetime
