from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.xhs.pc_api_adapter import XhsPcApiAdapter
from app.core.database import get_db
from app.core.deps import require_current_user
from app.core.security import decrypt_text
from app.models import AccountCookieVersion, PlatformAccount, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/xhs/pc", tags=["xhs-pc"])


def _get_owned_account(db: Session, current_user: User, account_id: int) -> PlatformAccount:
    account = db.get(PlatformAccount, account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _get_latest_cookies(db: Session, account: PlatformAccount) -> str:
    cookie_version = db.scalars(
        select(AccountCookieVersion)
        .where(AccountCookieVersion.platform_account_id == account.id)
        .order_by(AccountCookieVersion.created_at.desc())
    ).first()
    if cookie_version is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No cookies found for account")
    return decrypt_text(cookie_version.encrypted_cookies)


class SearchNotesRequest(BaseModel):
    account_id: int
    keyword: str = Field(min_length=1, max_length=200)
    page: int = Field(default=1, ge=1)
    sort_type_choice: int = Field(default=0)
    note_type: int = Field(default=0)
    note_time: int = Field(default=0)
    note_range: int = Field(default=0)
    pos_distance: int = Field(default=0)
    geo: str = Field(default="")


class NoteDetailRequest(BaseModel):
    account_id: int
    url: str = Field(min_length=1, max_length=4000)


class NoteCommentsRequest(BaseModel):
    account_id: int
    note_url: str = Field(min_length=1, max_length=4000)


def _parse_search_result(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        items_raw = raw.get("items", [])
        items = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            note_card = item.get("note_card") or item.get("note") or item
            if not isinstance(note_card, dict):
                continue
            user_info = note_card.get("user") or note_card.get("author") or {}
            interact = note_card.get("interact_info") or note_card.get("interaction") or {}
            items.append({
                "note_id": note_card.get("note_id") or note_card.get("id") or "",
                "note_url": note_card.get("note_url") or note_card.get("url") or "",
                "title": note_card.get("display_title") or note_card.get("title") or "",
                "content": note_card.get("desc") or note_card.get("content") or "",
                "author_id": user_info.get("user_id") or user_info.get("id") or "",
                "author_name": user_info.get("nickname") or user_info.get("name") or "",
                "author_avatar": user_info.get("avatar") or user_info.get("avatar_url") or "",
                "cover_url": note_card.get("cover", {}).get("url", "") if isinstance(note_card.get("cover"), dict) else note_card.get("cover_url", ""),
                "likes": interact.get("liked_count") or interact.get("likes") or 0,
                "collects": interact.get("collected_count") or interact.get("collects") or 0,
                "comments": interact.get("comment_count") or interact.get("comments") or 0,
                "shares": interact.get("share_count") or interact.get("shares") or 0,
                "type": note_card.get("type") or "",
                "image_urls": [img.get("url_default") or img.get("url", "") for img in (note_card.get("image_list") or []) if isinstance(img, dict)],
                "tags": [tag.get("name", "") for tag in (note_card.get("tag_list") or []) if isinstance(tag, dict)],
                "raw": item,
            })
        return {
            "total": raw.get("total", len(items)),
            "page": raw.get("page", 1),
            "page_size": raw.get("page_size", 20),
            "has_more": raw.get("has_more", False),
            "items": items,
            "raw": raw,
        }
    return {"total": 0, "page": 1, "page_size": 20, "has_more": False, "items": [], "raw": {}}


def _parse_note_detail(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = raw.get("data", raw)
        items = data.get("items", [data]) if isinstance(data, dict) else [data]
        note_item = items[0] if items else {}
        if not isinstance(note_item, dict):
            note_item = {}
        note_card = note_item.get("note_card") or note_item.get("note") or note_item
        if not isinstance(note_card, dict):
            note_card = {}
        user_info = note_card.get("user") or note_card.get("author") or {}
        interact = note_card.get("interact_info") or note_card.get("interaction") or {}
        video = note_card.get("video") or {}
        video_media = video.get("media", {}) if isinstance(video, dict) else {}
        stream = video_media.get("stream", {}) if isinstance(video_media, dict) else {}
        h264 = stream.get("h264", [{}]) if isinstance(stream, dict) else [{}]
        h264_first = h264[0] if h264 else {}
        origin_video_key = ""
        if isinstance(video, dict):
            consumer = video.get("consumer", {})
            if isinstance(consumer, dict):
                origin_video_key = consumer.get("origin_video_key", "")
        video_addr = h264_first.get("master_url") or h264_first.get("url") or ""
        if origin_video_key and not video_addr:
            video_addr = f"https://sns-video-bd.xhscdn.com/{origin_video_key}"
        return {
            "note_id": note_card.get("note_id") or note_card.get("id") or "",
            "note_url": note_card.get("note_url") or note_card.get("url") or "",
            "title": note_card.get("display_title") or note_card.get("title") or "",
            "content": note_card.get("desc") or note_card.get("content") or "",
            "author_id": user_info.get("user_id") or user_info.get("id") or "",
            "author_name": user_info.get("nickname") or user_info.get("name") or "",
            "author_avatar": user_info.get("avatar") or user_info.get("avatar_url") or "",
            "cover_url": note_card.get("cover", {}).get("url", "") if isinstance(note_card.get("cover"), dict) else note_card.get("cover_url", ""),
            "likes": interact.get("liked_count") or interact.get("likes") or 0,
            "collects": interact.get("collected_count") or interact.get("collects") or 0,
            "comments": interact.get("comment_count") or interact.get("comments") or 0,
            "shares": interact.get("share_count") or interact.get("shares") or 0,
            "type": note_card.get("type") or "",
            "image_urls": [img.get("url_default") or img.get("url", "") for img in (note_card.get("image_list") or []) if isinstance(img, dict)],
            "video_url": video.get("url", "") if isinstance(video, dict) else "",
            "video_addr": video_addr,
            "tags": [tag.get("name", "") for tag in (note_card.get("tag_list") or []) if isinstance(tag, dict)],
            "raw": raw,
        }
    return {"note_id": "", "note_url": "", "title": "", "content": "", "author_id": "", "author_name": "", "author_avatar": "", "cover_url": "", "likes": 0, "collects": 0, "comments": 0, "shares": 0, "type": "", "image_urls": [], "video_url": "", "video_addr": "", "tags": [], "raw": {}}


def _parse_comments(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [
            {
                "id": c.get("id", ""),
                "comment_id": str(c.get("id", "")),
                "user_name": c.get("nickname", c.get("user_name", "")),
                "user_id": str(c.get("user_id", "")),
                "content": c.get("content", ""),
                "like_count": int(c.get("like_count", 0) or 0),
                "parent_comment_id": str(c.get("sub_comment_id", "")) if c.get("sub_comment_id") else None,
                "raw": c,
            }
            for c in raw
            if isinstance(c, dict)
        ]
    if isinstance(raw, dict):
        comments = raw.get("comments", raw.get("data", []))
        if isinstance(comments, list):
            return _parse_comments(comments)
    return []


@router.post("/search/notes")
def search_notes(
    payload: SearchNotesRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = _get_owned_account(db, current_user, payload.account_id)
    cookies_text = _get_latest_cookies(db, account)
    adapter = XhsPcApiAdapter(cookies_text)
    try:
        raw = adapter.search_note(
            keyword=payload.keyword,
            page=payload.page,
            sort_type_choice=payload.sort_type_choice,
            note_type=payload.note_type,
            note_time=payload.note_time,
            note_range=payload.note_range,
            pos_distance=payload.pos_distance,
            geo=payload.geo,
        )
    except Exception as exc:
        logger.exception("XHS search failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"搜索失败: {exc}") from exc
    return _parse_search_result(raw)


@router.post("/notes/detail")
def get_note_detail(
    payload: NoteDetailRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = _get_owned_account(db, current_user, payload.account_id)
    cookies_text = _get_latest_cookies(db, account)
    adapter = XhsPcApiAdapter(cookies_text)
    try:
        raw = adapter.get_note_info(url=payload.url)
    except Exception as exc:
        logger.exception("XHS note detail failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取笔记详情失败: {exc}") from exc
    return _parse_note_detail(raw)


@router.post("/notes/comments")
def get_note_comments(
    payload: NoteCommentsRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = _get_owned_account(db, current_user, payload.account_id)
    cookies_text = _get_latest_cookies(db, account)
    adapter = XhsPcApiAdapter(cookies_text)
    try:
        raw = adapter.get_note_comments(note_url=payload.note_url)
    except Exception as exc:
        logger.exception("XHS note comments failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"获取评论失败: {exc}") from exc
    comments = _parse_comments(raw)
    return {"total": len(comments), "items": comments}
