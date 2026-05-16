# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SupportedRawPlatform = Literal["xhs", "dy", "zhihu"]
SourceType = Literal["keyword", "competitor_account", "manual_post"]


class RawItemInput(BaseModel):
    raw_id: str
    post_raw_id: str | None = None
    url: str | None = None
    content_text: str | None = None
    author_name: str | None = None
    published_at: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class RawFixtureInput(BaseModel):
    posts: list[RawItemInput] = Field(default_factory=list)
    comments: list[RawItemInput] = Field(default_factory=list)


class CrawlTaskCreateRequest(BaseModel):
    platform: SupportedRawPlatform
    source_type: SourceType
    source_value: str
    login_type: Literal["qrcode", "phone", "cookie"] = "cookie"
    enable_comments: bool = True
    enable_sub_comments: bool = False
    max_posts: int = Field(default=20, ge=1, le=1000)
    headless: bool = False
    cookies: str = ""
    fixture: RawFixtureInput | None = None


class CrawlTaskResponse(BaseModel):
    id: int
    platform: str
    source_type: str
    source_value: str
    crawler_type: str
    status: str
    error_message: str | None = None
    post_count: int
    comment_count: int
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str
    updated_at: str


class RawItemResponse(BaseModel):
    id: int
    task_id: int
    platform: str
    source_type: str
    source_value: str
    raw_id: str
    post_raw_id: str | None = None
    url: str | None = None
    content_text: str | None = None
    author_name: str | None = None
    published_at: str | None = None
    raw_data: dict[str, Any]
    created_at: str


class RawListResponse(BaseModel):
    items: list[RawItemResponse]
    total: int
    page: int
    page_size: int
