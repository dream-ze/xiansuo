from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx

from app.collectors.base import CollectionAuthError, CollectionRequestError


class XhsPcClient:
    def __init__(
        self,
        base_url: str = "https://edith.xiaohongshu.com",
        timeout: float = 20.0,
        signer: Any | None = None,
    ) -> None:
        cookies = (os.getenv("XHS_COOKIES") or "").strip()

        self._signer = signer
        self._use_signer = signer is not None

        if self._use_signer:
            cookies = signer.get_cookies_string() or cookies

        if not cookies and not self._use_signer:
            raise CollectionAuthError("XHS_COOKIES is required for real xhs collection")

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
                "Cookie": cookies,
            },
        )

    def close(self) -> None:
        self._client.close()

    def _sign_request(self, path: str, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> dict[str, str]:
        if not self._signer:
            return {}

        full_url = f"https://edith.xiaohongshu.com{path}"
        sign_payload = json_body if json_body else (params or {})

        try:
            sign_headers = self._signer.sign(full_url, sign_payload)
            if sign_headers:
                self._client.headers.update(sign_headers)
            return sign_headers
        except Exception:
            return {}

    def search_notes(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        bounded_limit = max(1, limit)
        while len(items) < bounded_limit:
            json_body = {
                "keyword": keyword,
                "page": page,
                "page_size": min(20, max(1, bounded_limit - len(items))),
                "search_id": uuid4().hex,
                "sort": "general",
                "note_type": 0,
                "ext_flags": [],
                "filters": [],
            }
            self._sign_request("/api/sns/web/v1/search/notes", json_body=json_body)
            response = self._request_json(
                method="POST",
                path="/api/sns/web/v1/search/notes",
                json=json_body,
            )
            batch = response.get("data", {}).get("items", [])
            for item in batch:
                if item.get("model_type") not in (None, "note") and "note_card" not in item:
                    continue
                items.append(item)
                if len(items) >= bounded_limit:
                    break

            has_more = bool(response.get("data", {}).get("has_more"))
            if not has_more or not batch:
                break
            page += 1
        return items

    def get_note_detail(self, post_url: str) -> dict[str, Any]:
        note_id, query = self._parse_note_url(post_url)
        json_body = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": "1"},
            "xsec_token": query.get("xsec_token", [""])[0],
            "xsec_source": query.get("xsec_source", ["pc_search"])[0],
        }
        self._sign_request("/api/sns/web/v1/feed", json_body=json_body)
        response = self._request_json(
            method="POST",
            path="/api/sns/web/v1/feed",
            json=json_body,
        )
        items = response.get("data", {}).get("items", [])
        if not items:
            raise CollectionRequestError(f"xhs note detail is empty for url: {post_url}")

        detail = dict(items[0])
        detail["url"] = post_url
        return detail

    def get_user_notes(self, account_url: str, limit: int) -> list[dict[str, Any]]:
        user_id, query = self._parse_user_url(account_url)
        cursor = ""
        items: list[dict[str, Any]] = []
        bounded_limit = max(1, limit)

        while len(items) < bounded_limit:
            params = {
                "num": min(30, max(1, bounded_limit - len(items))),
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": query.get("xsec_token", [""])[0],
                "xsec_source": query.get("xsec_source", ["pc_search"])[0],
            }
            self._sign_request("/api/sns/web/v1/user_posted", params=params)
            response = self._request_json(
                method="GET",
                path="/api/sns/web/v1/user_posted",
                params=params,
            )
            notes = response.get("data", {}).get("notes", [])
            for note in notes:
                items.append(note)
                if len(items) >= bounded_limit:
                    break

            cursor = str(response.get("data", {}).get("cursor") or "")
            has_more = bool(response.get("data", {}).get("has_more"))
            if not has_more or not notes:
                break
        return items

    def get_note_comments(
        self,
        post_id: str,
        post_url: str,
        xsec_token: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        _, query = self._parse_note_url(post_url)
        token = xsec_token or query.get("xsec_token", [""])[0]
        cursor = ""
        results: list[dict[str, Any]] = []
        bounded_limit = max(1, limit)

        while len(results) < bounded_limit:
            params = {
                "note_id": post_id,
                "cursor": cursor,
                "top_comment_id": "",
                "image_formats": "jpg,webp,avif",
                "xsec_token": token,
            }
            self._sign_request("/api/sns/web/v2/comment/page", params=params)
            response = self._request_json(
                method="GET",
                path="/api/sns/web/v2/comment/page",
                params=params,
            )
            comments = response.get("data", {}).get("comments", [])
            for raw_comment in comments:
                normalized = dict(raw_comment)
                normalized["note_id"] = normalized.get("note_id") or post_id
                results.append(normalized)
                if len(results) >= bounded_limit:
                    break

                for sub_comment in raw_comment.get("sub_comments", []) or []:
                    child = dict(sub_comment)
                    child["note_id"] = child.get("note_id") or post_id
                    results.append(child)
                    if len(results) >= bounded_limit:
                        break
                if len(results) >= bounded_limit:
                    break

            cursor = str(response.get("data", {}).get("cursor") or "")
            has_more = bool(response.get("data", {}).get("has_more"))
            if not has_more or not comments:
                break
        return results

    def _request_json(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method=method, url=path, params=params, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise CollectionAuthError("XHS_COOKIES is invalid or expired") from error
            raise CollectionRequestError(
                f"xhs request failed with status {error.response.status_code}"
            ) from error
        except httpx.HTTPError as error:
            raise CollectionRequestError(f"xhs request failed: {error}") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise CollectionRequestError("xhs response is not valid JSON") from error

        if not isinstance(payload, dict):
            raise CollectionRequestError("xhs response is not a JSON object")

        self._ensure_success(payload)
        return payload

    def _ensure_success(self, payload: dict[str, Any]) -> None:
        success = payload.get("success")
        code = payload.get("code")
        is_failed = success is False or (code not in (None, 0, "0") and success is not True)
        if not is_failed:
            return

        message = str(payload.get("msg") or payload.get("message") or "xhs request failed")
        lowered = message.lower()
        if any(token in lowered for token in ["cookie", "auth", "login", "过期", "登录"]):
            raise CollectionAuthError("XHS_COOKIES is invalid or expired")
        raise CollectionRequestError(message)

    def _parse_user_url(self, account_url: str) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(account_url)
        user_id = parsed.path.rstrip("/").split("/")[-1]
        if not user_id:
            raise CollectionRequestError("invalid xhs account url")
        return user_id, parse_qs(parsed.query)

    def _parse_note_url(self, post_url: str) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(post_url)
        note_id = parsed.path.rstrip("/").split("/")[-1]
        if not note_id:
            raise CollectionRequestError("invalid xhs post url")
        return note_id, parse_qs(parsed.query)
