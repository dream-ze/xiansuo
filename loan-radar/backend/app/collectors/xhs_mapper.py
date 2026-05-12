from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.collectors.base import CollectedComment, CollectedPost


def _pick(source: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        for candidate in (normalized, normalized.replace("/", "-")):
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
    return None


def _author_profile_url(author_id: str | None, raw_user: dict[str, Any]) -> str | None:
    explicit = _pick(raw_user, "profile_url", "user_page_url", "url")
    if explicit:
        return str(explicit)
    if author_id:
        return f"https://www.xiaohongshu.com/user/profile/{author_id}"
    return None


def _is_hot(like_count: int, comment_count: int, collect_count: int) -> bool:
    interaction_score = like_count + comment_count * 3 + collect_count * 2
    return interaction_score >= 100 or like_count >= 80 or comment_count >= 20


def normalize_post(raw_note: dict[str, Any]) -> CollectedPost:
    note = raw_note.get("note_card") if isinstance(raw_note.get("note_card"), dict) else raw_note
    interact_info = note.get("interact_info") or raw_note.get("interact_info") or {}
    user = note.get("user") or raw_note.get("user") or note.get("author") or {}

    post_id = str(_pick(note, "note_id", "id") or _pick(raw_note, "note_id", "id") or "")
    title = _pick(note, "title", "display_title")
    content = _pick(note, "desc", "content", "note_text")
    author_id = str(_pick(user, "user_id", "id") or "") or None
    xsec_token = _pick(raw_note, "xsec_token", "token") or _pick(note, "xsec_token", "token")

    like_count = _as_int(_pick(interact_info, "liked_count", "like_count"))
    comment_count = _as_int(_pick(interact_info, "comment_count", "comments_count"))
    collect_count = _as_int(_pick(interact_info, "collected_count", "collect_count"))

    post_url = _pick(raw_note, "url", "post_url") or _pick(note, "url", "post_url")
    if not post_url and post_id:
        post_url = f"https://www.xiaohongshu.com/explore/{post_id}"
        if xsec_token:
            post_url = f"{post_url}?xsec_token={xsec_token}&xsec_source=pc_search"

    return CollectedPost(
        platform="xhs",
        post_id=post_id,
        title=str(title) if title else None,
        content=str(content) if content else None,
        post_url=str(post_url) if post_url else None,
        author_name=str(_pick(user, "nickname", "nick_name", "name")) if _pick(user, "nickname", "nick_name", "name") else None,
        author_profile_url=_author_profile_url(author_id, user),
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        publish_time=_parse_datetime(_pick(note, "time", "publish_time", "last_update_time", "create_time")),
        is_hot=_is_hot(like_count, comment_count, collect_count),
        raw_data=raw_note,
    )


def normalize_comment(raw_comment: dict[str, Any]) -> CollectedComment:
    user = raw_comment.get("user_info") or raw_comment.get("user") or {}
    post_id = str(_pick(raw_comment, "note_id", "post_id", "target_id") or "")
    comment_id = str(_pick(raw_comment, "id", "comment_id") or "")
    user_id = str(_pick(user, "user_id", "id") or "") or None

    return CollectedComment(
        platform="xhs",
        post_id=post_id,
        comment_id=comment_id,
        user_name=str(_pick(user, "nickname", "nick_name", "name")) if _pick(user, "nickname", "nick_name", "name") else None,
        user_profile_url=_author_profile_url(user_id, user),
        content=str(_pick(raw_comment, "content", "text")) if _pick(raw_comment, "content", "text") else None,
        like_count=_as_int(_pick(raw_comment, "like_count", "liked_count")),
        publish_time=_parse_datetime(_pick(raw_comment, "create_time", "publish_time", "time")),
        raw_data=raw_comment,
    )