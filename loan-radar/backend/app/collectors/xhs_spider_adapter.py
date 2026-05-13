from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from app.collectors.base import CollectionAuthError, CollectionRequestError


def _sanitize_error_message(message: str) -> str:
    sanitized = message
    sanitized = re.sub(r"cookie\s*[:=]\s*[^\s,;]+", "cookie=***", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(token|api[_-]?key|authorization|session|web_session)\s*[:=]\s*[^\s,;]+", "token=***", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"([?&](token|api_key|apikey|auth|authorization|session|web_session)=)[^&\s]+", r"\1***", sanitized, flags=re.IGNORECASE)
    return sanitized


def _looks_like_auth_error(message: str) -> bool:
    lowered = message.lower()
    keywords = ["cookie", "auth", "login", "expired", "session", "登录", "过期", "鉴权"]
    return any(word in lowered for word in keywords)


class SpiderXhsAdapter:
    """Adapter around Spider_XHS public APIs for read-only collection flows."""

    def __init__(
        self,
        cookies: str | None = None,
        proxies: dict[str, str] | None = None,
        spider_path: str | None = None,
        api_client: Any | None = None,
    ) -> None:
        self.cookies = (cookies or os.getenv("XHS_COOKIES") or "").strip()
        self.proxies = proxies
        self._api = api_client

        path = (spider_path or os.getenv("XHS_SPIDER_PATH") or "").strip()
        if path:
            candidate = str(Path(path).resolve())
            if candidate not in sys.path:
                sys.path.insert(0, candidate)

    def _ensure_api(self) -> Any:
        if self._api is not None:
            return self._api

        try:
            from apis.xhs_pc_apis import XHS_Apis  # type: ignore
        except Exception as error:
            raise CollectionRequestError(
                "Spider_XHS is not available. Please set XHS_SPIDER_PATH to the Spider_XHS repo root."
            ) from error

        self._api = XHS_Apis()
        return self._api

    def _require_cookies(self) -> str:
        if not self.cookies:
            raise CollectionAuthError("XHS_COOKIES is required for spider xhs collection")
        return self.cookies

    def _handle_result(self, success: Any, message: Any, payload: Any) -> Any:
        if bool(success):
            return payload

        raw_message = str(message or "spider_xhs request failed")
        sanitized = _sanitize_error_message(raw_message)
        if _looks_like_auth_error(raw_message):
            raise CollectionAuthError("XHS_COOKIES is invalid or expired")
        raise CollectionRequestError(sanitized)

    def search_notes(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        cookies = self._require_cookies()
        api = self._ensure_api()
        success, message, payload = api.search_some_note(keyword, max(1, limit), cookies, proxies=self.proxies)
        data = self._handle_result(success, message, payload)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            items = (data.get("data") or {}).get("items") if isinstance(data.get("data"), dict) else None
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    def get_note_detail(self, post_url: str) -> dict[str, Any]:
        cookies = self._require_cookies()
        api = self._ensure_api()
        success, message, payload = api.get_note_info(post_url, cookies, proxies=self.proxies)
        data = self._handle_result(success, message, payload)

        if isinstance(data, dict):
            root_data = data.get("data") if isinstance(data.get("data"), dict) else None
            items = root_data.get("items") if isinstance(root_data, dict) else None
            if isinstance(items, list) and items:
                note = dict(items[0])
                note.setdefault("url", post_url)
                return note

            note = dict(data)
            note.setdefault("url", post_url)
            return note

        raise CollectionRequestError("spider_xhs note detail format is invalid")

    def get_note_comments(self, post_url: str, limit: int) -> list[dict[str, Any]]:
        cookies = self._require_cookies()
        api = self._ensure_api()
        success, message, payload = api.get_note_all_comment(post_url, cookies, proxies=self.proxies)
        data = self._handle_result(success, message, payload)

        flattened: list[dict[str, Any]] = []
        if isinstance(data, list):
            for comment in data:
                if not isinstance(comment, dict):
                    continue
                normalized = dict(comment)
                flattened.append(normalized)
                sub_comments = normalized.get("sub_comments") or []
                if isinstance(sub_comments, list):
                    for child in sub_comments:
                        if isinstance(child, dict):
                            flattened.append(dict(child))

        bounded = max(1, limit)
        return flattened[:bounded]