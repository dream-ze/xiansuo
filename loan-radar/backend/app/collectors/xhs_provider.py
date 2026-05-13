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
from app.collectors.xhs_browser_signer import XhsBrowserSigner
from app.collectors.xhs_metrics import classify_provider_error, get_driver_metrics_recorder
from app.collectors.xhs_cdp_client import XhsCdpClient, sanitize_cdp_error
from app.collectors.xhs_pc_client import XhsPcClient
from app.collectors.xhs_spider_adapter import SpiderXhsAdapter
from app.collectors.xhs_mapper import normalize_comment, normalize_post


class XhsProvider:
    def __init__(
        self,
        cookies: str | None = None,
        client: Any | None = None,
        cdp_client: Any | None = None,
        spider_adapter: Any | None = None,
        signer: Any | None = None,
        metrics_recorder: Any | None = None,
        base_url: str = "https://edith.xiaohongshu.com",
        cdp_endpoint: str | None = None,
        cdp_browser_channel: str | None = None,
    ):
        _ = cookies
        self.cookies = (os.getenv("XHS_COOKIES") or "").strip()
        self.driver = (os.getenv("XHS_PROVIDER_DRIVER") or "browser").strip().lower()
        self.cdp_endpoint = (cdp_endpoint or os.getenv("XHS_CDP_ENDPOINT") or "http://127.0.0.1:9222").strip()
        self.cdp_browser_channel = (cdp_browser_channel or os.getenv("XHS_CDP_BROWSER_CHANNEL") or "").strip() or None
        self.fallback_to_pc = (os.getenv("XHS_PROVIDER_FALLBACK_TO_PC") or "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        self._own_client = client is None
        self._own_cdp_client = cdp_client is None
        self._own_spider_adapter = spider_adapter is None
        self._own_signer = signer is None
        self._base_url = base_url
        self.client = client
        self.cdp_client = cdp_client
        self.spider_adapter = spider_adapter
        self.signer = signer
        self.metrics = metrics_recorder or get_driver_metrics_recorder()

        normalized = self._normalize_driver()
        if normalized == "pc" and self.client is None:
            self._require_cookies_or_signer()
            self.client = XhsPcClient(base_url=self._base_url, signer=self.signer)
        elif normalized == "browser" and self.client is None:
            self.client = self._init_browser_client()

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
        if self._own_cdp_client and self.cdp_client is not None and hasattr(self.cdp_client, "close"):
            self.cdp_client.close()
        if self._own_spider_adapter and self.spider_adapter is not None and hasattr(self.spider_adapter, "close"):
            self.spider_adapter.close()

    def _require_cookies_or_signer(self) -> None:
        if self.signer is not None:
            return
        if not self.cookies:
            raise CollectionAuthError("XHS_COOKIES is required for real xhs collection (or use browser driver)")

    def _init_browser_client(self) -> XhsPcClient | None:
        if self.signer is None:
            self.signer = XhsBrowserSigner.get_instance()

        if not self.signer.is_started:
            try:
                self.signer.start()
            except Exception as error:
                raise CollectionAuthError(
                    f"Failed to start browser signer. Please login first via /api/xhs-auth/start-login: {error}"
                ) from error

        if not self.signer.is_logged_in:
            raise CollectionAuthError(
                "XHS browser is not logged in. Please login first via /api/xhs-auth/start-login"
            )

        return XhsPcClient(base_url=self._base_url, signer=self.signer)

    def collect_by_keyword(self, keyword: str, limit: int) -> ProviderCollectionResult:
        items = self._collect_raw_posts(keyword=keyword, limit=limit)
        posts = [normalize_post(item) for item in items]

        if not posts:
            raise CollectionNoDataError(f"no xhs posts found for keyword: {keyword}")
        return ProviderCollectionResult(
            posts=posts,
            metadata={
                "query": keyword,
                "entry": "keyword",
                "driver": self.driver,
                "driver_metrics": self.metrics.snapshot(),
            },
        )

    def collect_by_account(self, account_url: str, limit: int) -> ProviderCollectionResult:
        notes = self._collect_raw_account_posts(account_url=account_url, limit=limit)
        posts = [normalize_post(note) for note in notes]

        if not posts:
            raise CollectionNoDataError(f"no xhs posts found for account: {account_url}")
        return ProviderCollectionResult(
            posts=posts,
            metadata={
                "account_url": account_url,
                "entry": "account",
                "driver": self.driver,
                "driver_metrics": self.metrics.snapshot(),
            },
        )

    def collect_by_post_url(self, post_url: str) -> ProviderCollectionResult:
        detail = self._collect_raw_note_detail(post_url=post_url)
        normalized = normalize_post(detail)
        if not normalized.post_id:
            raise CollectionNoDataError(f"no xhs post found for url: {post_url}")
        return ProviderCollectionResult(
            posts=[normalized],
            metadata={
                "post_url": post_url,
                "entry": "post_url",
                "driver": self.driver,
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
        raw_comments = self._collect_raw_comments(post_id=post_id, post_url=post_url, xsec_token=xsec_token, limit=limit)
        comments: list[CollectedComment] = []
        for raw_comment in raw_comments:
            payload = dict(raw_comment)
            payload["note_id"] = payload.get("note_id") or post_id
            comments.append(normalize_comment(payload))
        return comments

    def _normalize_driver(self) -> str:
        if self.driver in {"pc", "spider", "cdp", "auto", "browser"}:
            return self.driver
        return "browser"

    def _get_pc_client(self) -> Any:
        if self.client is None:
            self._require_cookies_or_signer()
            self.client = XhsPcClient(base_url=self._base_url, signer=self.signer)
        return self.client

    def _get_cdp_client(self) -> Any:
        if self.cdp_client is None:
            self.cdp_client = XhsCdpClient(
                endpoint=self.cdp_endpoint,
                browser_channel=self.cdp_browser_channel,
            )
        return self.cdp_client

    def _get_spider_adapter(self) -> Any:
        if self.spider_adapter is None:
            self.spider_adapter = SpiderXhsAdapter(cookies=self.cookies)
        return self.spider_adapter

    def _get_browser_signer(self) -> XhsBrowserSigner:
        if self.signer is None:
            self.signer = XhsBrowserSigner.get_instance()
        return self.signer

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
            raise_error = error
            if driver == "cdp" and isinstance(error, CollectionRequestError):
                raise_error = CollectionRequestError(sanitize_cdp_error(str(error)))
            classified = classify_provider_error(raise_error)
            self.metrics.record(
                driver=driver,
                operation=operation,
                duration_ms=(time.perf_counter() - started) * 1000,
                success=False,
                failure_type=f"{classified.level}.{classified.error_type}",
            )
            raise raise_error from error

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

        if driver == "browser":
            return self._run_driver_operation(
                "browser",
                "keyword_search",
                lambda: self._get_pc_client().search_notes(keyword=keyword, limit=limit),
            )

        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "keyword_search",
                lambda: self._get_pc_client().search_notes(keyword=keyword, limit=limit),
            )

        if driver == "cdp":
            return self._run_driver_operation(
                "cdp",
                "keyword_search",
                lambda: self._get_cdp_client().search_notes(keyword=keyword, limit=limit),
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
                        lambda: self._get_pc_client().search_notes(keyword=keyword, limit=limit),
                    )
                raise

        try:
            return self._run_driver_operation(
                "browser",
                "keyword_search",
                lambda: self._get_pc_client().search_notes(keyword=keyword, limit=limit),
            )
        except (CollectionRequestError, CollectionAuthError):
            pass

        try:
            return self._run_driver_operation(
                "cdp",
                "keyword_search",
                lambda: self._get_cdp_client().search_notes(keyword=keyword, limit=limit),
            )
        except (CollectionRequestError, CollectionAuthError):
            pass

        try:
            return self._collect_spider_keyword_posts(keyword=keyword, limit=limit)
        except (CollectionRequestError, CollectionAuthError):
            return self._run_driver_operation(
                "pc",
                "keyword_search",
                lambda: self._get_pc_client().search_notes(keyword=keyword, limit=limit),
            )

    def _collect_raw_account_posts(self, account_url: str, limit: int) -> list[dict[str, Any]]:
        driver = self._normalize_driver()

        if driver == "browser":
            return self._run_driver_operation(
                "browser",
                "account_posts",
                lambda: self._get_pc_client().get_user_notes(account_url=account_url, limit=limit),
            )

        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "account_posts",
                lambda: self._get_pc_client().get_user_notes(account_url=account_url, limit=limit),
            )

        if driver == "cdp":
            raise CollectionRequestError("xhs cdp account collection is not supported")

        if driver == "spider":
            if self.fallback_to_pc:
                return self._run_driver_operation(
                    "pc",
                    "account_posts",
                    lambda: self._get_pc_client().get_user_notes(account_url=account_url, limit=limit),
                )
            raise CollectionRequestError("Spider_XHS account collection is not supported in this adapter")

        return self._run_driver_operation(
            "browser",
            "account_posts",
            lambda: self._get_pc_client().get_user_notes(account_url=account_url, limit=limit),
        )

    def _collect_raw_note_detail(self, post_url: str) -> dict[str, Any]:
        driver = self._normalize_driver()

        if driver == "browser":
            return self._run_driver_operation(
                "browser",
                "note_detail",
                lambda: self._get_pc_client().get_note_detail(post_url=post_url),
            )

        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "note_detail",
                lambda: self._get_pc_client().get_note_detail(post_url=post_url),
            )

        if driver == "cdp":
            return self._run_driver_operation(
                "cdp",
                "note_detail",
                lambda: self._get_cdp_client().get_note_detail(post_url=post_url),
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
                        lambda: self._get_pc_client().get_note_detail(post_url=post_url),
                    )
                raise

        try:
            return self._run_driver_operation(
                "browser",
                "note_detail",
                lambda: self._get_pc_client().get_note_detail(post_url=post_url),
            )
        except (CollectionRequestError, CollectionAuthError):
            pass

        try:
            return self._run_driver_operation(
                "cdp",
                "note_detail",
                lambda: self._get_cdp_client().get_note_detail(post_url=post_url),
            )
        except (CollectionRequestError, CollectionAuthError):
            pass

        try:
            return self._run_driver_operation(
                "spider",
                "note_detail",
                lambda: self._get_spider_adapter().get_note_detail(post_url=post_url),
            )
        except (CollectionRequestError, CollectionAuthError):
            return self._run_driver_operation(
                "pc",
                "note_detail",
                lambda: self._get_pc_client().get_note_detail(post_url=post_url),
            )

    def _collect_raw_comments(self, post_id: str, post_url: str, xsec_token: str, limit: int) -> list[dict[str, Any]]:
        driver = self._normalize_driver()

        if driver == "browser":
            return self._run_driver_operation(
                "browser",
                "note_comments",
                lambda: self._get_pc_client().get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )

        if driver == "pc":
            return self._run_driver_operation(
                "pc",
                "note_comments",
                lambda: self._get_pc_client().get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )

        if driver == "cdp":
            return self._run_driver_operation(
                "cdp",
                "note_comments",
                lambda: self._get_cdp_client().get_note_comments(
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
                        lambda: self._get_pc_client().get_note_comments(
                            post_id=post_id,
                            post_url=post_url,
                            xsec_token=xsec_token,
                            limit=limit,
                        ),
                    )
                raise

        try:
            return self._run_driver_operation(
                "browser",
                "note_comments",
                lambda: self._get_pc_client().get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )
        except (CollectionRequestError, CollectionAuthError):
            pass

        try:
            return self._run_driver_operation(
                "cdp",
                "note_comments",
                lambda: self._get_cdp_client().get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )
        except (CollectionRequestError, CollectionAuthError):
            pass

        try:
            return self._run_driver_operation(
                "spider",
                "note_comments",
                lambda: self._get_spider_adapter().get_note_comments(post_url=spider_post_url, limit=limit),
            )
        except (CollectionRequestError, CollectionAuthError):
            return self._run_driver_operation(
                "pc",
                "note_comments",
                lambda: self._get_pc_client().get_note_comments(
                    post_id=post_id,
                    post_url=post_url,
                    xsec_token=xsec_token,
                    limit=limit,
                ),
            )
