from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from app.collectors.base import CollectionAuthError, CollectionRequestError

PLATFORM_NAME_MAP: dict[str, str] = {
    "xhs": "xhs",
    "douyin": "dy",
    "zhihu": "zhihu",
    # Future: kuaishou -> ks, bilibili -> bili, weibo -> wb, tieba -> tieba
}

CRAWL_TYPE_MAP: dict[str, str] = {
    "search": "search",
    "detail": "detail",
    "creator": "creator",
}


class MediaCrawlerBridge:
    """HTTP client for MediaCrawler API service.

    MediaCrawler runs as an independent service:
        uv run uvicorn api.main:app --port 8080 --reload

    Workflow:
        1. POST /api/crawler/start  → launch async crawl subprocess
        2. GET  /api/crawler/status → poll until idle
        3. GET  /api/data/files     → find latest data files
        4. GET  /api/data/files/{path}?preview=true → read collected data
    """

    DEFAULT_API_BASE = "http://127.0.0.1:8080"
    DEFAULT_TIMEOUT = 300
    POLL_INTERVAL = 5
    MAX_POLL_ATTEMPTS = 120

    def __init__(
        self,
        api_base_url: str | None = None,
        timeout: int | None = None,
    ):
        self.api_base_url = (
            api_base_url
            or os.getenv("MEDIA_CRAWLER_API_URL", "")
            or self.DEFAULT_API_BASE
        ).rstrip("/")
        self.timeout = timeout or int(
            os.getenv("MEDIA_CRAWLER_TIMEOUT", str(self.DEFAULT_TIMEOUT))
        )

    def _mc_platform(self, platform: str) -> str:
        mc_platform = PLATFORM_NAME_MAP.get(platform, platform)
        return mc_platform

    def health_check(self) -> bool:
        try:
            from app.collectors.media_crawler.shared_db_reader import is_shared_db_available
            if is_shared_db_available():
                return True
        except Exception:
            pass
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/health",
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _ensure_idle(self, max_wait: int = 30) -> None:
        """Ensure MediaCrawler is idle. Stop running crawl if needed."""
        try:
            status_data = self.get_crawl_status()
        except CollectionRequestError:
            return

        state = status_data.get("status", "idle")
        if state == "idle":
            return

        if state in ("running", "stopping"):
            try:
                self.stop_crawl()
            except CollectionRequestError:
                pass

            for _ in range(max_wait // self.POLL_INTERVAL + 1):
                time.sleep(self.POLL_INTERVAL)
                try:
                    current = self.get_crawl_status()
                except CollectionRequestError:
                    break
                if current.get("status") == "idle":
                    break

    def create_crawl_task(
        self,
        platform: str,
        source_type: str,
        source_value: str,
        login_type: str = "cookie",
        max_posts: int = 20,
        enable_comments: bool = True,
        cookies: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "platform": self._mc_platform(platform),
            "source_type": source_type,
            "source_value": source_value,
            "login_type": login_type,
            "enable_comments": enable_comments,
            "max_posts": max_posts,
        }
        if cookies:
            payload["cookies"] = cookies

        try:
            resp = httpx.post(
                f"{self.api_base_url}/api/crawl-tasks",
                json=payload,
                timeout=120,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                f"MediaCrawler 服务无法连接 ({self.api_base_url})，"
                "请先启动 MediaCrawler API 服务：\n"
                "  cd D:\\Project\\MediaCrawler\n"
                "  uv run uvicorn api.main:app --port 8080 --reload"
            ) from error
        except httpx.TimeoutException as error:
            raise CollectionRequestError(
                f"MediaCrawler API 请求超时 ({self.timeout}s)"
            ) from error

    def get_task(self, task_id: int) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/crawl-tasks/{task_id}",
                timeout=30,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError("MediaCrawler 服务无法连接") from error

    def list_raw_posts(self, task_id: int) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/crawl-tasks/{task_id}/raw-posts",
                params={"page": 1, "page_size": 500},
                timeout=30,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError("MediaCrawler 服务无法连接") from error

    def list_raw_comments(self, task_id: int) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/crawl-tasks/{task_id}/raw-comments",
                params={"page": 1, "page_size": 500},
                timeout=30,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError("MediaCrawler 服务无法连接") from error

    def wait_for_task_result(self, task_id: int, platform: str) -> dict[str, Any]:
        if self._try_shared_db_result(task_id, platform):
            return self._try_shared_db_result(task_id, platform)

        for _ in range(self.MAX_POLL_ATTEMPTS):
            task = self.get_task(task_id)
            status = task.get("status")
            if status == "success":
                posts, comments = self._read_task_data(task_id, platform)
                return {
                    "platform": platform,
                    "posts": posts,
                    "comments": comments,
                }
            if status == "failed":
                raise CollectionRequestError(
                    f"MediaCrawler 采集失败: {task.get('error_message') or 'unknown error'}"
                )
            time.sleep(self.POLL_INTERVAL)

        raise CollectionRequestError(f"MediaCrawler 任务超时: task_id={task_id}")

    def _try_shared_db_result(self, task_id: int, platform: str) -> dict[str, Any] | None:
        try:
            from app.collectors.media_crawler.shared_db_reader import SharedRawTaskReader
            reader = SharedRawTaskReader()
            task = reader.get_task(task_id)
            if task is None:
                return None
            if task.get("status") == "success":
                posts_data = reader.list_raw_posts(task_id, page=1, page_size=500)
                comments_data = reader.list_raw_comments(task_id, page=1, page_size=500)
                posts = [_raw_item_payload(item) for item in posts_data.get("items", [])]
                comments = [_raw_item_payload(item) for item in comments_data.get("items", [])]
                return {
                    "platform": platform,
                    "posts": posts,
                    "comments": comments,
                }
        except Exception:
            pass
        return None

    def _read_task_data(self, task_id: int, platform: str) -> tuple[list[dict], list[dict]]:
        try:
            posts_resp = self.list_raw_posts(task_id)
            comments_resp = self.list_raw_comments(task_id)
            posts = [_raw_item_payload(item) for item in posts_resp.get("items", [])]
            comments = [_raw_item_payload(item) for item in comments_resp.get("items", [])]
            return posts, comments
        except Exception:
            return [], []

    def start_crawl(
        self,
        platform: str,
        crawl_type: str,
        source_value: str,
        login_type: str = "cookie",
        max_notes: int = 20,
        enable_comments: bool = True,
        cookies: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_idle()

        mc_platform = self._mc_platform(platform)
        mc_crawl_type = CRAWL_TYPE_MAP.get(crawl_type, crawl_type)

        payload: dict[str, Any] = {
            "platform": mc_platform,
            "crawler_type": mc_crawl_type,
            "login_type": login_type,
            "enable_comments": enable_comments,
            "save_option": "json",
            "headless": False,
        }

        if mc_crawl_type == "search" and source_value:
            payload["keywords"] = source_value
        elif mc_crawl_type == "detail" and source_value:
            payload["specified_ids"] = self._parse_ids(source_value)
        elif mc_crawl_type == "creator" and source_value:
            payload["creator_ids"] = source_value

        if cookies:
            payload["cookies"] = cookies

        try:
            resp = httpx.post(
                f"{self.api_base_url}/api/crawler/start",
                json=payload,
                timeout=30,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                f"MediaCrawler 服务无法连接 ({self.api_base_url})，"
                "请先启动 MediaCrawler API 服务：\n"
                "  cd D:\\Project\\MediaCrawler\n"
                "  uv run uvicorn api.main:app --port 8080 --reload"
            ) from error
        except httpx.TimeoutException as error:
            raise CollectionRequestError(
                f"MediaCrawler API 请求超时 ({self.timeout}s)"
            ) from error

    def get_crawl_status(self) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/crawler/status",
                timeout=15,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                "MediaCrawler 服务无法连接"
            ) from error

    def get_crawl_logs(self, limit: int = 50) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/crawler/logs",
                params={"limit": limit},
                timeout=15,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                "MediaCrawler 服务无法连接"
            ) from error

    def stop_crawl(self) -> dict[str, Any]:
        try:
            resp = httpx.post(
                f"{self.api_base_url}/api/crawler/stop",
                timeout=15,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                "MediaCrawler 服务无法连接"
            ) from error

    def list_data_files(
        self,
        platform: str | None = None,
        file_type: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if platform:
            mc_platform = self._mc_platform(platform)
            params["platform"] = mc_platform
        if file_type:
            params["file_type"] = file_type

        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/data/files",
                params=params,
                timeout=15,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                "MediaCrawler 服务无法连接"
            ) from error

    def get_data_file_content(
        self,
        file_path: str,
        limit: int = 500,
    ) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/data/files/{file_path}",
                params={"preview": True, "limit": limit},
                timeout=30,
            )
            return self._handle_response(resp)
        except httpx.ConnectError as error:
            raise CollectionRequestError(
                "MediaCrawler 服务无法连接"
            ) from error

    def wait_for_crawl_and_collect(
        self,
        platform: str,
        started_at: float | None = None,
    ) -> dict[str, Any]:
        """Poll crawl status until idle, then read the latest data files.

        Returns: {"platform": str, "posts": [...], "comments": [...]}
        """
        saw_running = False
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                status_data = self.get_crawl_status()
            except CollectionRequestError:
                time.sleep(self.POLL_INTERVAL)
                continue

            state = status_data.get("status", "idle")

            if state == "running":
                saw_running = True
                time.sleep(self.POLL_INTERVAL)
                continue

            if state == "stopping":
                time.sleep(self.POLL_INTERVAL)
                continue

            if state == "error":
                error_msg = status_data.get("error_message", "unknown error")
                raise CollectionRequestError(
                    f"MediaCrawler 采集失败: {error_msg}"
                )

            if state == "idle" and saw_running:
                break

            if state == "idle" and not saw_running:
                if attempt > 6:
                    break
                time.sleep(self.POLL_INTERVAL)
                continue

            time.sleep(self.POLL_INTERVAL)

        time.sleep(3)

        return self._read_latest_data_files(platform, started_at)

    def _read_latest_data_files(
        self,
        platform: str,
        started_at: float | None = None,
    ) -> dict[str, Any]:
        files_data = self.list_data_files(platform=platform, file_type="json")

        files = files_data.get("files", [])
        if not files:
            files_data = self.list_data_files(platform=platform)
            files = files_data.get("files", [])

        if started_at is not None:
            files = [f for f in files if f.get("modified_at", 0) >= started_at - 60]

        if not files:
            return {"platform": platform, "posts": [], "comments": []}

        files.sort(key=lambda f: f.get("modified_at", 0), reverse=True)

        all_posts: list[dict[str, Any]] = []
        all_comments: list[dict[str, Any]] = []

        for file_info in files[:5]:
            file_path = file_info.get("path", "")
            if not file_path:
                continue

            try:
                content_data = self.get_data_file_content(file_path, limit=500)
            except Exception:
                continue

            data = content_data.get("data")
            if data is None:
                continue

            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    if self._is_comment_item(item):
                        all_comments.append(item)
                    else:
                        all_posts.append(item)
            elif isinstance(data, dict):
                posts = data.get("posts") or data.get("notes") or []
                comments = data.get("comments") or []
                if isinstance(posts, list):
                    all_posts.extend(p for p in posts if isinstance(p, dict))
                if isinstance(comments, list):
                    all_comments.extend(c for c in comments if isinstance(c, dict))

        return {
            "platform": platform,
            "posts": all_posts,
            "comments": all_comments,
        }

    _AUTH_ERROR_PATTERNS = (
        "当前账号存在异常",
        "账号异常",
        "请切换账号",
        "登录已过期",
        "login required",
        "unauthorized",
        "session expired",
        "P2:request",
    )

    def _handle_response(self, resp: httpx.Response) -> dict[str, Any]:
        if resp.status_code == 401:
            raise CollectionAuthError(
                "采集认证失败：Cookie 已过期或账号被风控，请重新获取 Cookie 后更新监控源配置。"
            )
        if resp.status_code == 404:
            raise CollectionRequestError(
                f"MediaCrawler API 端点不存在: {resp.url}"
            )
        if resp.status_code >= 500:
            raise CollectionRequestError(
                f"MediaCrawler 服务错误: {resp.status_code} {resp.text[:500]}"
            )
        if resp.status_code >= 400:
            try:
                error_data = resp.json()
                error_msg = error_data.get("message", error_data.get("detail", resp.text[:500]))
            except Exception:
                error_msg = resp.text[:500]

            if self._is_auth_error(error_msg):
                raise CollectionAuthError(
                    f"采集认证失败：平台返回「{error_msg}」，Cookie 已过期或账号被风控，请重新获取 Cookie 后更新监控源配置。"
                )
            if "already running" in str(error_msg).lower():
                raise CollectionRequestError(
                    "MediaCrawler 当前有采集任务正在运行，请等待完成后再试，"
                    "或前往 MediaCrawler WebUI (http://127.0.0.1:8080) 手动停止。"
                )
            raise CollectionRequestError(f"MediaCrawler API 错误: {error_msg}")

        try:
            data = resp.json()
        except Exception as error:
            raise CollectionRequestError(
                f"解析 MediaCrawler 响应失败: {error}"
            ) from error

        if isinstance(data, dict):
            error_msg = data.get("error_message") or data.get("error") or ""
            if error_msg and self._is_auth_error(str(error_msg)):
                raise CollectionAuthError(
                    f"采集认证失败：平台返回「{error_msg}」，Cookie 已过期或账号被风控，请重新获取 Cookie 后更新监控源配置。"
                )

        return data

    @classmethod
    def _is_auth_error(cls, message: str) -> bool:
        lower = message.lower()
        return any(pattern.lower() in lower for pattern in cls._AUTH_ERROR_PATTERNS)

    def _parse_ids(self, source_value: str) -> str:
        if not source_value:
            return ""
        values = [v.strip() for v in source_value.split(",") if v.strip()]
        result_ids = []
        for val in values:
            if val.startswith("http"):
                parts = val.rstrip("/").split("/")
                result_ids.append(parts[-1])
            else:
                result_ids.append(val)
        return ",".join(result_ids)

    def _is_comment_item(self, item: dict[str, Any]) -> bool:
        comment_keys = {"content", "comment_id", "note_id", "user_info", "sub_comments"}
        return bool(set(item.keys()) & comment_keys)


def _raw_item_payload(item: dict[str, Any]) -> dict[str, Any]:
    raw_data = item.get("raw_data")
    if isinstance(raw_data, dict) and raw_data:
        return raw_data
    return {
        "id": item.get("raw_id"),
        "post_id": item.get("post_raw_id"),
        "content": item.get("content_text"),
        "author_name": item.get("author_name"),
        "url": item.get("url"),
        "publish_time": item.get("published_at"),
    }
