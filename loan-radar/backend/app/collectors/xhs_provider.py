from __future__ import annotations

import os
import time
from types import TracebackType
from typing import Any

from app.collectors.base import (
    CollectedComment,
    CollectionAuthError,
    CollectionNoDataError,
    CollectionRequestError,
    ProviderCollectionResult,
)
from app.collectors.xhs_metrics import classify_provider_error, get_driver_metrics_recorder
from app.collectors.xhs_pc_client import XhsPcClient
from app.collectors.xhs_spider_adapter import SpiderXhsAdapter
from app.collectors.xhs_mapper import normalize_comment, normalize_post


class XhsProvider:
    def __init__(
        self,
        cookies: str | None = None,
        client: Any | None = None,
        spider_adapter: Any | None = None,
        metrics_recorder: Any | None = None,
        base_url: str = "https://edith.xiaohongshu.com",
    ):
        # For security and consistent runtime behavior, cookies are read from env only.
        _ = cookies
        self.cookies = (os.getenv("XHS_COOKIES") or "").strip()
        self.driver = (os.getenv("XHS_PROVIDER_DRIVER") or "pc").strip().lower()
        self.fallback_to_pc = (os.getenv("XHS_PROVIDER_FALLBACK_TO_PC") or "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        self._own_client = client is None
        self._own_spider_adapter = spider_adapter is None
        self.client = client or XhsPcClient(base_url=base_url)
        self.spider_adapter = spider_adapter
        self.metrics = metrics_recorder or get_driver_metrics_recorder()

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
        if self._own_client and hasattr(self.client, "close"):
            self.client.close()
        if self._own_spider_adapter and self.spider_adapter is not None and hasattr(self.spider_adapter, "close"):
            self.spider_adapter.close()

    def _require_cookies(self) -> str:
        if not self.cookies:
            raise CollectionAuthError("XHS_COOKIES is required for real xhs collection")
        return self.cookies

    def collect_by_keyword(self, keyword: str, limit: int) -> ProviderCollectionResult:
        self._require_cookies()
        items = self._collect_raw_posts(keyword=keyword, limit=limit)
        posts = [normalize_post(item) for item in items]

        if not posts:
            raise CollectionNoDataError(f"no xhs posts found for keyword: {keyword}")
        return ProviderCollectionResult(
            posts=posts,
            metadata={
                "query": keyword,
                "entry": "keyword",
                "driver_metrics": self.metrics.snapshot(),
            },
        )

    def collect_by_account(self, account_url: str, limit: int) -> ProviderCollectionResult:
        self._require_cookies()
        notes = self._collect_raw_account_posts(account_url=account_url, limit=limit)
        posts = [normalize_post(note) for note in notes]

        if not posts:
            raise CollectionNoDataError(f"no xhs posts found for account: {account_url}")
        return ProviderCollectionResult(
            posts=posts,
            metadata={
                "account_url": account_url,
                "entry": "account",
                "driver_metrics": self.metrics.snapshot(),
            },
        )

    def collect_by_post_url(self, post_url: str) -> ProviderCollectionResult:
        self._require_cookies()
        detail = self._collect_raw_note_detail(post_url=post_url)
        normalized = normalize_post(detail)
        if not normalized.post_id:
            raise CollectionNoDataError(f"no xhs post found for url: {post_url}")
        return ProviderCollectionResult(
            posts=[normalized],
            metadata={
                "post_url": post_url,
                "entry": "post_url",
                "driver_metrics": self.metrics.snapshot(),
            },
        )

    def collect_comments(
        self,
        post_id: str,
        post_url: str,
        xsec_token: str,
        limit: int = 50,
    ) -> list[CollectedComment]:
        self._require_cookies()
        raw_comments = self._collect_raw_comments(post_id=post_id, post_url=post_url, xsec_token=xsec_token, limit=limit)
        comments: list[CollectedComment] = []
        for raw_comment in raw_comments:
            payload = dict(raw_comment)
            payload["note_id"] = payload.get("note_id") or post_id
            comments.append(normalize_comment(payload))
        return comments

    def _normalize_driver(self) -> str:
        if self.driver in {"pc", "spider", "auto"}:
            return self.driver
        return "pc"

    def _get_spider_adapter(self) -> Any:
        if self.spider_adapter is None:
            self.spider_adapter = SpiderXhsAdapter(cookies=self.cookies)
        return self.spider_adapter

    def _run_driver_operation(self, driver: str, operation: str, func: Any) -> Any:
        started = time.perf_counter()
        try:
            result = func()
            self.metrics.record(
                driver=driver,
                operation=operation,
                duration_ms=(time.perf_counter() - started) * 1000,
                success=True,
            )
            return result
        except Exception as error:
            classified = classify_provider_error(error)
            self.metrics.record(
                driver=driver,
                operation=operation,
                duration_ms=(time.perf_counter() - started) * 1000,
                success=False,
                failure_type=f"{classified.level}.{classified.error_type}",
            )
            raise

    def _resolve_spider_post_url(self, note: dict[str, Any]) -> str:
        explicit_url = note.get("url") or note.get("post_url")
        if isinstance(explicit_url, str) and explicit_url.strip():
            return explicit_url.strip()

        note_card = note.get("note_card") if isinstance(note.get("note_card"), dict) else {}
        note_id = str(note_card.get("note_id") or note_card.get("id") or note.get("note_id") or note.get("id") or "").strip()
        if not note_id:
            return ""

        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        xsec_token = str(note.get("xsec_token") or note_card.get("xsec_token") or "").strip()
        if xsec_token:
            url = f"{url}?xsec_token={xsec_token}&xsec_source=pc_search"
        return url

    def _collect_spider_keyword_posts(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        spider = self._get_spider_adapter()
        notes = self._run_driver_operation(
            "spider",
            "keyword_search",
            lambda: spider.search_notes(keyword=keyword, limit=limit),
        )

        if not isinstance(notes, list):
            return []

        enriched: list[dict[str, Any]] = []
        for raw_note in notes:
            if not isinstance(raw_note, dict):
                continue

            post_url = self._resolve_spider_post_url(raw_note)
            if not post_url:
                enriched.append(dict(raw_note))
                continue

            try:
                detail = self._run_driver_operation(
                    "spider",
                    "note_detail",
                    lambda url=post_url: spider.get_note_detail(post_url=url),
                )
                merged = dict(raw_note)
                if isinstance(detail, dict):
                    merged.update(detail)
                merged.setdefault("url", post_url)
                enriched.append(merged)
            except (CollectionAuthError, CollectionNoDataError):
                raise
            except CollectionRequestError:
                fallback_note = dict(raw_note)
                fallback_note.setdefault("url", post_url)
                enriched.append(fallback_note)

        return enriched

    def _collect_raw_posts(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        driver = self._normalize_driver()
        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "keyword_search",
                lambda: self.client.search_notes(keyword=keyword, limit=limit),
            )

        if driver == "spider":
            try:
                return self._collect_spider_keyword_posts(keyword=keyword, limit=limit)
            except (CollectionAuthError, CollectionNoDataError):
                raise
            except CollectionRequestError:
                if self.fallback_to_pc:
                    return self._run_driver_operation(
                        "pc",
                        "keyword_search",
                        lambda: self.client.search_notes(keyword=keyword, limit=limit),
                    )
                raise

        try:
            return self._collect_spider_keyword_posts(keyword=keyword, limit=limit)
        except CollectionRequestError:
            return self._run_driver_operation(
                "pc",
                "keyword_search",
                lambda: self.client.search_notes(keyword=keyword, limit=limit),
            )

    def _collect_raw_account_posts(self, account_url: str, limit: int) -> list[dict[str, Any]]:
        driver = self._normalize_driver()
        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "account_posts",
                lambda: self.client.get_user_notes(account_url=account_url, limit=limit),
            )

        if driver == "spider":
            if self.fallback_to_pc:
                return self._run_driver_operation(
                    "pc",
                    "account_posts",
                    lambda: self.client.get_user_notes(account_url=account_url, limit=limit),
                )
            raise CollectionRequestError("Spider_XHS account collection is not supported in this adapter")

        return self._run_driver_operation(
            "pc",
            "account_posts",
            lambda: self.client.get_user_notes(account_url=account_url, limit=limit),
        )

    def _collect_raw_note_detail(self, post_url: str) -> dict[str, Any]:
        driver = self._normalize_driver()
        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "note_detail",
                lambda: self.client.get_note_detail(post_url=post_url),
            )

        if driver == "spider":
            try:
                return self._run_driver_operation(
                    "spider",
                    "note_detail",
                    lambda: self._get_spider_adapter().get_note_detail(post_url=post_url),
                )
            except (CollectionAuthError, CollectionNoDataError):
                raise
            except CollectionRequestError:
                if self.fallback_to_pc:
                    return self._run_driver_operation(
                        "pc",
                        "note_detail",
                        lambda: self.client.get_note_detail(post_url=post_url),
                    )
                raise

        try:
            return self._run_driver_operation(
                "spider",
                "note_detail",
                lambda: self._get_spider_adapter().get_note_detail(post_url=post_url),
            )
        except CollectionRequestError:
            return self._run_driver_operation(
                "pc",
                "note_detail",
                lambda: self.client.get_note_detail(post_url=post_url),
            )

    def _collect_raw_comments(self, post_id: str, post_url: str, xsec_token: str, limit: int) -> list[dict[str, Any]]:
        driver = self._normalize_driver()
        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "note_comments",
                lambda: self.client.get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )

        spider_post_url = post_url or f"https://www.xiaohongshu.com/explore/{post_id}"
        if xsec_token and "xsec_token=" not in spider_post_url:
            sep = "&" if "?" in spider_post_url else "?"
            spider_post_url = f"{spider_post_url}{sep}xsec_token={xsec_token}&xsec_source=pc_search"

        if driver == "spider":
            try:
                return self._run_driver_operation(
                    "spider",
                    "note_comments",
                    lambda: self._get_spider_adapter().get_note_comments(post_url=spider_post_url, limit=limit),
                )
            except (CollectionAuthError, CollectionNoDataError):
                raise
            except CollectionRequestError:
                if self.fallback_to_pc:
                    return self._run_driver_operation(
                        "pc",
                        "note_comments",
                        lambda: self.client.get_note_comments(
                            post_id=post_id,
                            post_url=post_url,
                            xsec_token=xsec_token,
                            limit=limit,
                        ),
                    )
                raise

        try:
            return self._run_driver_operation(
                "spider",
                "note_comments",
                lambda: self._get_spider_adapter().get_note_comments(post_url=spider_post_url, limit=limit),
            )
        except CollectionRequestError:
            return self._run_driver_operation(
                "pc",
                "note_comments",
                lambda: self.client.get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )
