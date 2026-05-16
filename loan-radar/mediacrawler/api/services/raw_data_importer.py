# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .raw_task_store import RawTaskStore


class RawDataImporter:
    """Import MediaCrawler JSON/JSONL outputs into the raw task SQLite store."""

    def __init__(self, data_dir: str | Path | None = None, store: RawTaskStore | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent.parent / "data"
        self.store = store or RawTaskStore()

    def import_latest_for_task(self, task_id: int) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"crawl task not found: {task_id}")

        platform = task["platform"]
        crawler_type = task["crawler_type"]
        source_type = task["source_type"]
        source_value = task["source_value"]

        for raw_post in self._read_latest_items(platform, crawler_type, "contents"):
            normalized = normalize_raw_post(raw_post, platform=platform)
            if not normalized["raw_id"]:
                continue
            self.store.insert_raw_post(
                task_id=task_id,
                platform=platform,
                source_type=source_type,
                source_value=source_value,
                **normalized,
            )

        for raw_comment in self._read_latest_items(platform, crawler_type, "comments"):
            normalized = normalize_raw_comment(raw_comment, platform=platform)
            if not normalized["raw_id"]:
                continue
            self.store.insert_raw_comment(
                task_id=task_id,
                platform=platform,
                source_type=source_type,
                source_value=source_value,
                **normalized,
            )

        self.store.mark_success(task_id)

    def _read_latest_items(self, platform: str, crawler_type: str, item_type: str) -> list[dict[str, Any]]:
        candidates: list[Path] = []
        for file_type in ("json", "jsonl"):
            folder = self.data_dir / platform / file_type
            if folder.exists():
                candidates.extend(folder.glob(f"{crawler_type}_{item_type}_*.{file_type}"))

        if not candidates:
            return []

        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        if latest.suffix == ".jsonl":
            items = []
            for line in latest.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    items.append(item)
            return items

        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []


def normalize_raw_post(raw: dict[str, Any], *, platform: str) -> dict[str, Any]:
    raw_id = _first(raw, _POST_ID_FIELDS.get(platform, ()), ("id", "post_id"))
    title = _first(raw, ("title", "display_title", "question_title"))
    body = _first(raw, ("desc", "content", "text", "text_raw", "excerpt", "description"))
    content_text = _join_text(title, body)
    return {
        "raw_id": str(raw_id or ""),
        "post_raw_id": None,
        "url": _first(raw, ("url", "post_url", "note_url", "aweme_url", "content_url", "share_url")),
        "content_text": content_text,
        "author_name": _first(raw, ("nickname", "author_name", "user_name", "name")),
        "published_at": _normalize_time(_first(raw, ("time", "create_time", "publish_time", "created_at"))),
        "raw_data": raw,
    }


def normalize_raw_comment(raw: dict[str, Any], *, platform: str) -> dict[str, Any]:
    raw_id = _first(raw, _COMMENT_ID_FIELDS.get(platform, ()), ("id", "comment_id"))
    post_raw_id = _first(raw, _POST_ID_FIELDS.get(platform, ()), ("post_id", "target_id", "content_id"))
    return {
        "raw_id": str(raw_id or ""),
        "post_raw_id": str(post_raw_id) if post_raw_id not in (None, "") else None,
        "url": _first(raw, ("url", "comment_url")),
        "content_text": _first(raw, ("content", "text", "text_raw", "message")),
        "author_name": _first(raw, ("nickname", "author_name", "user_name", "name")),
        "published_at": _normalize_time(_first(raw, ("create_time", "publish_time", "created_at"))),
        "raw_data": raw,
    }


_POST_ID_FIELDS = {
    "xhs": ("note_id",),
    "dy": ("aweme_id", "aweme_id_str"),
    "zhihu": ("content_id", "question_id", "answer_id"),
}

_COMMENT_ID_FIELDS = {
    "xhs": ("comment_id",),
    "dy": ("comment_id", "cid"),
    "zhihu": ("comment_id",),
}


def _first(raw: dict[str, Any], *field_groups: tuple[str, ...]) -> Any | None:
    for fields in field_groups:
        for field in fields:
            value = raw.get(field)
            if value not in (None, ""):
                return value
    return None


def _join_text(*values: Any | None) -> str | None:
    parts = [str(value) for value in values if value not in (None, "")]
    return "\n".join(parts) if parts else None


def _normalize_time(value: Any | None) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            return None
    return str(value)
