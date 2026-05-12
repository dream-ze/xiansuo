from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CollectedPost(BaseModel):
    platform: str
    post_id: str
    title: str | None = None
    content: str | None = None
    post_url: str | None = None
    author_name: str | None = None
    author_profile_url: str | None = None
    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    publish_time: datetime | None = None
    is_hot: bool = False
    raw_data: Any | None = None


class CollectedComment(BaseModel):
    platform: str
    post_id: str
    comment_id: str
    user_name: str | None = None
    user_profile_url: str | None = None
    content: str | None = None
    like_count: int = 0
    publish_time: datetime | None = None
    raw_data: Any | None = None


class CollectorResult(BaseModel):
    posts: list[CollectedPost] = Field(default_factory=list)
    comments: list[CollectedComment] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, source: Any) -> CollectorResult:
        raise NotImplementedError
