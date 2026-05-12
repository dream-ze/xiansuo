from __future__ import annotations

import os
from types import TracebackType
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx

from app.collectors.base import (
    CollectionAuthError,
    CollectionNoDataError,
    CollectionRequestError,
    ProviderCollectionResult,
)
from app.collectors.xhs_mapper import normalize_comment, normalize_post


class _HttpTransport:
    def __init__(self, base_url: str, cookies: str, timeout: float = 20.0):
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.xiaohongshu.com",
                "Referer": "https://www.xiaohongshu.com/",
            },
        )
        self._client.headers["Cookie"] = cookies

    def close(self) -> None:
        self._client.close()

    def get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=payload)
        response.raise_for_status()
        return response.json()


class XhsProvider:
    def __init__(
        self,
        cookies: str | None = None,
        transport: Any | None = None,
        base_url: str = "https://edith.xiaohongshu.com",
    ):
        self.cookies = (cookies or os.getenv("XHS_COOKIES") or "").strip()
        self._own_transport = transport is None
        self.transport = transport or _HttpTransport(base_url=base_url, cookies=self._require_cookies())

    def __enter__(self) -> "XhsProvider":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._own_transport and hasattr(self.transport, "close"):
            self.transport.close()

    def _require_cookies(self) -> str:
        if not self.cookies:
            raise CollectionAuthError("XHS_COOKIES is required for real xhs collection")
        return self.cookies

    def _handle_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise CollectionRequestError("xhs response is not a JSON object")

        success = payload.get("success", True)
        if success:
            return payload

        message = str(payload.get("msg") or payload.get("message") or "xhs request failed")
        lowered = message.lower()
        if any(keyword in lowered for keyword in ["login", "cookie", "auth", "登录", "过期"]):
            raise CollectionAuthError("XHS_COOKIES is invalid or expired")
        raise CollectionRequestError(message)

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_cookies()
        try:
            return self._handle_response(self.transport.get_json(path, params))
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise CollectionAuthError("XHS_COOKIES is invalid or expired") from error
            raise CollectionRequestError(f"xhs request failed with status {error.response.status_code}") from error
        except httpx.HTTPError as error:
            raise CollectionRequestError(f"xhs request failed: {error}") from error

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_cookies()
        try:
            return self._handle_response(self.transport.post_json(path, payload))
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise CollectionAuthError("XHS_COOKIES is invalid or expired") from error
            raise CollectionRequestError(f"xhs request failed with status {error.response.status_code}") from error
        except httpx.HTTPError as error:
            raise CollectionRequestError(f"xhs request failed: {error}") from error

    def collect_by_keyword(self, keyword: str, limit: int) -> ProviderCollectionResult:
        page = 1
        posts = []
        while len(posts) < limit:
            response = self._post_json(
                "/api/sns/web/v1/search/notes",
                {
                    "keyword": keyword,
                    "page": page,
                    "page_size": min(20, max(1, limit - len(posts))),
                    "search_id": uuid4().hex,
                    "sort": "general",
                    "note_type": 0,
                    "ext_flags": [],
                    "filters": [],
                },
            )
            items = response.get("data", {}).get("items", [])
            for item in items:
                if item.get("model_type") not in (None, "note") and "note_card" not in item:
                    continue
                posts.append(normalize_post(item))
                if len(posts) >= limit:
                    break
            has_more = bool(response.get("data", {}).get("has_more"))
            if not has_more or not items:
                break
            page += 1

        if not posts:
            raise CollectionNoDataError(f"no xhs posts found for keyword: {keyword}")
        return ProviderCollectionResult(posts=posts, metadata={"query": keyword, "entry": "keyword"})

    def collect_by_account(self, account_url: str, limit: int) -> ProviderCollectionResult:
        user_id, query = self._parse_user_url(account_url)
        cursor = ""
        posts = []
        while len(posts) < limit:
            response = self._get_json(
                "/api/sns/web/v1/user_posted",
                {
                    "num": min(30, max(1, limit - len(posts))),
                    "cursor": cursor,
                    "user_id": user_id,
                    "image_formats": "jpg,webp,avif",
                    "xsec_token": query.get("xsec_token", [""])[0],
                    "xsec_source": query.get("xsec_source", ["pc_search"])[0],
                },
            )
            notes = response.get("data", {}).get("notes", [])
            for note in notes:
                posts.append(normalize_post(note))
                if len(posts) >= limit:
                    break
            cursor = str(response.get("data", {}).get("cursor") or "")
            if not response.get("data", {}).get("has_more") or not notes:
                break

        if not posts:
            raise CollectionNoDataError(f"no xhs posts found for account: {account_url}")
        return ProviderCollectionResult(posts=posts, metadata={"account_url": account_url, "entry": "account"})

    def collect_by_post_url(self, post_url: str) -> ProviderCollectionResult:
        note_id, query = self._parse_note_url(post_url)
        response = self._post_json(
            "/api/sns/web/v1/feed",
            {
                "source_note_id": note_id,
                "image_formats": ["jpg", "webp", "avif"],
                "extra": {"need_body_topic": "1"},
                "xsec_token": query.get("xsec_token", [""])[0],
                "xsec_source": query.get("xsec_source", ["pc_search"])[0],
            },
        )
        items = response.get("data", {}).get("items", [])
        if not items:
            raise CollectionNoDataError(f"no xhs post found for url: {post_url}")

        normalized = normalize_post({**items[0], "url": post_url})
        return ProviderCollectionResult(posts=[normalized], metadata={"post_url": post_url, "entry": "post_url"})

    def collect_comments(self, post_id: str, post_url: str, xsec_token: str) -> list:
        _, query = self._parse_note_url(post_url)
        token = xsec_token or query.get("xsec_token", [""])[0]
        cursor = ""
        comments = []
        while True:
            response = self._get_json(
                "/api/sns/web/v2/comment/page",
                {
                    "note_id": post_id,
                    "cursor": cursor,
                    "top_comment_id": "",
                    "image_formats": "jpg,webp,avif",
                    "xsec_token": token,
                },
            )
            raw_comments = response.get("data", {}).get("comments", [])
            for raw_comment in raw_comments:
                raw_comment["note_id"] = raw_comment.get("note_id") or post_id
                comments.append(normalize_comment(raw_comment))
                for sub_comment in raw_comment.get("sub_comments", []) or []:
                    sub_comment["note_id"] = sub_comment.get("note_id") or post_id
                    comments.append(normalize_comment(sub_comment))
            cursor = str(response.get("data", {}).get("cursor") or "")
            if not response.get("data", {}).get("has_more") or not raw_comments:
                break
        return comments

    def _parse_user_url(self, user_url: str) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(user_url)
        user_id = parsed.path.rstrip("/").split("/")[-1]
        if not user_id:
            raise CollectionRequestError("invalid xhs account url")
        return user_id, parse_qs(parsed.query)

    def _parse_note_url(self, note_url: str) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(note_url)
        note_id = parsed.path.rstrip("/").split("/")[-1]
        if not note_id:
            raise CollectionRequestError("invalid xhs post url")
        return note_id, parse_qs(parsed.query)