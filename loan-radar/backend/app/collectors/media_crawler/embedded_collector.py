"""Embedded MediaCrawler collector - 直接调用 MediaCrawler Python API，跳过 HTTP 中间层。

当 MediaCrawler 包可 import 时自动启用，否则 fallback 到 HTTP bridge。

使用方式：
  1. pip install -e "./mediacrawler"
  2. 设置环境变量 MEDIA_CRAWLER_HOME=./mediacrawler
  3. loan-radar 启动时自动检测并使用 embedded 模式
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

from app.collectors.base import (
    BaseCollector,
    CollectionAuthError,
    CollectionNoDataError,
    CollectionRequestError,
    CollectorResult,
    CollectedComment,
    CollectedPost,
)
from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS, map_platform_data

_SOURCE_TYPE_TO_CRAWLER_TYPE = {
    "keyword": "search",
    "competitor_account": "creator",
    "manual_post": "detail",
    "hot_post_rule": "search",
}

_PLATFORM_TO_MC_PLATFORM = {
    "xhs": "xhs",
    "douyin": "dy",
    "zhihu": "zhihu",
}

_MC_PLATFORM_TO_OURS = {v: k for k, v in _PLATFORM_TO_MC_PLATFORM.items()}


def _get_mc_home() -> str | None:
    home = os.getenv("MEDIA_CRAWLER_HOME")
    if not home:
        return None
    p = Path(home)
    if not p.is_absolute():
        p = Path(os.getcwd()) / home
    return str(p)


def _is_embedded_available() -> bool:
    home = _get_mc_home()
    if not home:
        return False
    return Path(home).is_dir()


class EmbeddedMediaCrawlerCollector(BaseCollector):
    """直接调用 MediaCrawler 的 CrawlerManager + RawTaskStore，无需 HTTP 服务。

    工作流：
      1. 通过 CrawlerManager 启动采集子进程
      2. 通过 RawTaskStore 轮询任务状态（直接读 SQLite）
      3. 从 RawTaskStore 读取 raw_posts / raw_comments
      4. 通过 mappers.py 映射为 CollectedPost / CollectedComment
    """

    POLL_INTERVAL = 3
    MAX_POLL_ATTEMPTS = 200

    def __init__(self):
        self._mc_home = _get_mc_home()
        if not self._mc_home:
            raise RuntimeError("MEDIA_CRAWLER_HOME not set")

    def collect(self, source: Any) -> CollectorResult:
        config = getattr(source, "config", None) or {}
        platform = getattr(source, "platform", "xhs")
        source_type = getattr(source, "source_type", "keyword")
        source_value = getattr(source, "value", "") or ""

        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"MediaCrawler 不支持平台 '{platform}'。"
                f"支持的平台: {', '.join(sorted(SUPPORTED_PLATFORMS))}"
            )

        if not source_value:
            raise ValueError("采集关键词/ID 不能为空")

        mc_platform = _PLATFORM_TO_MC_PLATFORM.get(platform, platform)
        crawl_type = _SOURCE_TYPE_TO_CRAWLER_TYPE.get(source_type, "search")

        max_posts = int(config.get("max_posts", 20)) if isinstance(config, dict) else 20
        enable_comments = bool(config.get("enable_comments", True)) if isinstance(config, dict) else True
        login_type = str(config.get("login_type", "qrcode")) if isinstance(config, dict) else "qrcode"
        cookies = (config.get("cookies") if isinstance(config, dict) else None) or os.getenv("MEDIA_CRAWLER_COOKIES", "") or None

        try:
            from api.services.raw_task_store import RawTaskStore
            from api.schemas.crawler import (
                CrawlerStartRequest,
                CrawlerTypeEnum,
                LoginTypeEnum,
                PlatformEnum,
                SaveDataOptionEnum,
            )
        except ImportError as exc:
            raise CollectionRequestError(
                f"无法 import MediaCrawler 模块，请确认 MEDIA_CRAWLER_HOME 设置正确 "
                f"且已执行 pip install -e '{self._mc_home}'。错误: {exc}"
            ) from exc

        store = RawTaskStore()
        task = store.create_task(
            platform=mc_platform,
            source_type=source_type,
            source_value=source_value,
            crawler_type=crawl_type,
        )
        task_id = task["id"]

        try:
            started = self._start_crawler_subprocess(
                mc_platform=mc_platform,
                crawl_type=crawl_type,
                source_value=source_value,
                login_type=login_type,
                enable_comments=enable_comments,
                max_posts=max_posts,
                cookies=cookies or "",
            )
        except Exception as exc:
            store.mark_failed(task_id, str(exc))
            raise CollectionRequestError(f"启动 MediaCrawler 子进程失败: {exc}") from exc

        if not started:
            store.mark_failed(task_id, "CrawlerManager 启动失败，可能已有任务在运行")
            raise CollectionRequestError("MediaCrawler 当前有任务正在运行，请等待完成后再试")

        store.mark_running(task_id)

        final_task = self._poll_until_done(store, task_id)

        if final_task["status"] == "failed":
            error_msg = final_task.get("error_message") or "unknown error"
            raise CollectionRequestError(f"MediaCrawler 采集失败: {error_msg}")

        raw_posts_data = store.list_raw_posts(task_id, page=1, page_size=500)
        raw_comments_data = store.list_raw_comments(task_id, page=1, page_size=500)

        raw_posts = [self._raw_item_to_dict(item) for item in raw_posts_data.get("items", [])]
        raw_comments = [self._raw_item_to_dict(item) for item in raw_comments_data.get("items", [])]

        mapped_data = {
            "platform": platform,
            "posts": raw_posts,
            "comments": raw_comments,
        }

        posts, comments = map_platform_data(mapped_data, platform)

        if not posts and not comments:
            raise CollectionNoDataError(
                f"MediaCrawler 未返回数据：platform={platform}, "
                f"type={crawl_type}, value={source_value[:100]}"
            )

        return CollectorResult(
            posts=posts,
            comments=comments,
            metadata={
                "source": "media_crawler_embedded",
                "platform": platform,
                "crawl_type": crawl_type,
                "total_posts": len(posts),
                "total_comments": len(comments),
            },
        )

    def _start_crawler_subprocess(
        self,
        mc_platform: str,
        crawl_type: str,
        source_value: str,
        login_type: str,
        enable_comments: bool,
        max_posts: int,
        cookies: str,
    ) -> bool:
        try:
            from api.services.crawler_manager import crawler_manager
            from api.schemas.crawler import (
                CrawlerStartRequest,
                CrawlerTypeEnum,
                LoginTypeEnum,
                PlatformEnum,
                SaveDataOptionEnum,
            )
        except ImportError:
            return False

        platform_enum = PlatformEnum(mc_platform)
        login_enum = LoginTypeEnum(login_type)
        crawler_enum = CrawlerTypeEnum(crawl_type)

        request = CrawlerStartRequest(
            platform=platform_enum,
            login_type=login_enum,
            crawler_type=crawler_enum,
            keywords=source_value if crawl_type == "search" else "",
            specified_ids=source_value if crawl_type == "detail" else "",
            creator_ids=source_value if crawl_type == "creator" else "",
            enable_comments=enable_comments,
            save_option=SaveDataOptionEnum.JSON,
            cookies=cookies or "",
            headless=False,
        )

        loop = asyncio.new_event_loop()
        try:
            started = loop.run_until_complete(crawler_manager.start(request))
        finally:
            loop.close()

        return bool(started)

    def _poll_until_done(self, store, task_id: int) -> dict[str, Any]:
        for _ in range(self.MAX_POLL_ATTEMPTS):
            task = store.get_task(task_id)
            if task is None:
                raise CollectionRequestError(f"crawl task {task_id} not found in RawTaskStore")

            status = task.get("status")
            if status in ("success", "failed"):
                return task

            if status == "running":
                try:
                    from api.services.crawler_manager import crawler_manager
                    mc_status = crawler_manager.status
                    if mc_status == "idle" and status == "running":
                        self._import_data_and_mark_success(store, task_id)
                        return store.get_task(task_id)
                    if mc_status == "error":
                        store.mark_failed(task_id, "MediaCrawler process failed")
                        return store.get_task(task_id)
                except ImportError:
                    pass

            time.sleep(self.POLL_INTERVAL)

        store.mark_failed(task_id, "poll timeout")
        return store.get_task(task_id)

    def _import_data_and_mark_success(self, store, task_id: int) -> None:
        try:
            from api.services.raw_data_importer import RawDataImporter
            importer = RawDataImporter(store=store)
            importer.import_latest_for_task(task_id)
        except Exception as exc:
            store.mark_failed(task_id, f"data import failed: {exc}")

    @staticmethod
    def _raw_item_to_dict(item: dict[str, Any]) -> dict[str, Any]:
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
