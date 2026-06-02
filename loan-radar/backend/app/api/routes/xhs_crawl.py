from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

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

router = APIRouter(prefix="/api/xhs/crawl", tags=["xhs-crawl"])


class CrawlDataRequest(BaseModel):
    account_id: int
    mode: Literal["note_urls", "search", "comments"] = "note_urls"
    urls: list[str] = Field(default_factory=list)
    keyword: str = Field(default="", max_length=200)
    pages: int = Field(default=1, ge=1, le=50)
    max_notes: int = Field(default=20, ge=1, le=200)
    time_sleep: float = Field(default=1, ge=0, le=10)
    fetch_comments: bool = False
    sort_type_choice: int = Field(default=0)
    note_type: int = Field(default=0)
    note_time: int = Field(default=0)
    note_range: int = Field(default=0)
    pos_distance: int = Field(default=0)
    geo: str = Field(default="")


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


def _parse_note_from_raw(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    data = raw.get("data", raw)
    items = data.get("items", [data]) if isinstance(data, dict) else [data]
    note_item = items[0] if items else {}
    if not isinstance(note_item, dict):
        return None
    note_card = note_item.get("note_card") or note_item.get("note") or note_item
    if not isinstance(note_card, dict):
        return None
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


def _parse_search_items(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    items_raw = raw.get("items", [])
    results = []
    for item in items_raw:
        if not isinstance(item, dict):
            continue
        note_card = item.get("note_card") or item.get("note") or item
        if not isinstance(note_card, dict):
            continue
        user_info = note_card.get("user") or note_card.get("author") or {}
        interact = note_card.get("interact_info") or note_card.get("interaction") or {}
        results.append({
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
    return results


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


def _sse_event(event_type: str, **kwargs) -> str:
    payload = {"type": event_type, **kwargs}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n"


@router.post("/data")
def crawl_data(
    payload: CrawlDataRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = _get_owned_account(db, current_user, payload.account_id)
    cookies_text = _get_latest_cookies(db, account)
    adapter = XhsPcApiAdapter(cookies_text)

    def generate():
        success_count = 0
        failed_count = 0
        total = 0

        try:
            if payload.mode == "search":
                yield _sse_event("progress", message=f"正在搜索: {payload.keyword}")
                for page in range(1, payload.pages + 1):
                    try:
                        raw = adapter.search_note(
                            keyword=payload.keyword,
                            page=page,
                            sort_type_choice=payload.sort_type_choice,
                            note_type=payload.note_type,
                            note_time=payload.note_time,
                            note_range=payload.note_range,
                            pos_distance=payload.pos_distance,
                            geo=payload.geo,
                        )
                        items = _parse_search_items(raw)
                        for idx, note in enumerate(items):
                            total += 1
                            comments = []
                            if payload.fetch_comments and note.get("note_url"):
                                try:
                                    raw_comments = adapter.get_note_comments(note_url=note["note_url"])
                                    comments = _parse_comments(raw_comments)
                                except Exception:
                                    pass
                            yield _sse_event("item", index=total - 1, item={
                                "source": note.get("note_url", ""),
                                "status": "success",
                                "error": "",
                                "note": note,
                                "comments": comments,
                                "comment_count": len(comments),
                            })
                            success_count += 1
                        if page < payload.pages:
                            time.sleep(min(payload.time_sleep, 3))
                    except Exception as exc:
                        failed_count += 1
                        total += 1
                        yield _sse_event("item", index=total - 1, item={
                            "source": f"search:{payload.keyword}:page{page}",
                            "status": "failed",
                            "error": str(exc)[:200],
                            "note": None,
                            "comments": [],
                            "comment_count": 0,
                        })
                        yield _sse_event("error", message=f"第 {page} 页搜索失败: {str(exc)[:100]}")

            elif payload.mode == "note_urls":
                urls = payload.urls or []
                total = len(urls)
                yield _sse_event("progress", message=f"开始抓取 {total} 个笔记")
                for idx, url in enumerate(urls):
                    try:
                        raw = adapter.get_note_info(url=url)
                        note = _parse_note_from_raw(raw)
                        comments = []
                        if payload.fetch_comments and note and note.get("note_url"):
                            try:
                                raw_comments = adapter.get_note_comments(note_url=note["note_url"])
                                comments = _parse_comments(raw_comments)
                            except Exception:
                                pass
                        yield _sse_event("item", index=idx, item={
                            "source": url,
                            "status": "success",
                            "error": "",
                            "note": note,
                            "comments": comments,
                            "comment_count": len(comments),
                        })
                        success_count += 1
                    except Exception as exc:
                        failed_count += 1
                        yield _sse_event("item", index=idx, item={
                            "source": url,
                            "status": "failed",
                            "error": str(exc)[:200],
                            "note": None,
                            "comments": [],
                            "comment_count": 0,
                        })
                        yield _sse_event("error", message=f"笔记 {url[:50]} 抓取失败: {str(exc)[:100]}")
                    if idx < len(urls) - 1:
                        time.sleep(min(payload.time_sleep, 3))

            elif payload.mode == "comments":
                urls = payload.urls or []
                total = len(urls)
                yield _sse_event("progress", message=f"开始抓取 {total} 个笔记的评论")
                for idx, url in enumerate(urls):
                    try:
                        raw_comments = adapter.get_note_comments(note_url=url)
                        comments = _parse_comments(raw_comments)
                        yield _sse_event("item", index=idx, item={
                            "source": url,
                            "status": "success",
                            "error": "",
                            "note": None,
                            "comments": comments,
                            "comment_count": len(comments),
                        })
                        success_count += 1
                    except Exception as exc:
                        failed_count += 1
                        yield _sse_event("item", index=idx, item={
                            "source": url,
                            "status": "failed",
                            "error": str(exc)[:200],
                            "note": None,
                            "comments": [],
                            "comment_count": 0,
                        })
                        yield _sse_event("error", message=f"评论抓取失败: {str(exc)[:100]}")
                    if idx < len(urls) - 1:
                        time.sleep(min(payload.time_sleep, 3))

        except Exception as exc:
            logger.exception("Crawl stream error")
            yield _sse_event("error", message=f"抓取异常: {str(exc)[:200]}")

        yield _sse_event("done", total=total, success_count=success_count, failed_count=failed_count)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
