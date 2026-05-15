from __future__ import annotations

import os
from typing import Any

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.media_crawler.bridge import MediaCrawlerBridge
from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS, map_platform_data


_SOURCE_TYPE_TO_CRAWL_TYPE = {
    "keyword": "search",
    "competitor_account": "creator",
    "manual_post": "detail",
    "hot_post_rule": "search",
}


class MediaCrawlerCollector(BaseCollector):
    """Collector that delegates to MediaCrawler API service.

    MediaCrawler must be running as an API service:
        cd D:\\Project\\MediaCrawler
        uv run uvicorn api.main:app --port 8080 --reload

    Workflow:
        1. POST /api/crawl-tasks  → create a MediaCrawler raw task
        2. GET  /api/crawl-tasks/{task_id} → poll task status
        3. GET  /api/crawl-tasks/{task_id}/raw-posts and /raw-comments
        4. Map raw data → CollectedPost / CollectedComment
    """

    def __init__(self):
        self._bridge = MediaCrawlerBridge()

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

        crawl_type = _SOURCE_TYPE_TO_CRAWL_TYPE.get(source_type, "search")

        max_posts = int(config.get("max_posts", 20)) if isinstance(config, dict) else 20
        enable_comments = bool(config.get("enable_comments", True)) if isinstance(config, dict) else True
        login_type = str(config.get("login_type", "qrcode")) if isinstance(config, dict) else "qrcode"
        cookies = (config.get("cookies") if isinstance(config, dict) else None) or os.getenv("MEDIA_CRAWLER_COOKIES", "") or None

        if not self._bridge.health_check():
            raise ConnectionError(
                f"MediaCrawler API 服务不可用 ({self._bridge.api_base_url})，"
                "请先启动 MediaCrawler：\n"
                "  cd D:\\Project\\MediaCrawler\n"
                "  uv run uvicorn api.main:app --port 8080 --reload"
            )

        task = self._bridge.create_crawl_task(
            platform=platform,
            source_type=source_type,
            source_value=source_value,
            login_type=login_type,
            max_posts=max_posts,
            enable_comments=enable_comments,
            cookies=cookies or None,
        )

        raw_data = self._bridge.wait_for_task_result(task_id=int(task["id"]), platform=platform)

        posts, comments = map_platform_data(raw_data, platform)

        if not posts and not comments:
            from app.collectors.base import CollectionNoDataError
            raise CollectionNoDataError(
                f"MediaCrawler 未返回数据：platform={platform}, "
                f"type={crawl_type}, value={source_value[:100]}"
            )

        return CollectorResult(
            posts=posts,
            comments=comments,
            metadata={
                "source": "media_crawler",
                "platform": platform,
                "crawl_type": crawl_type,
                "total_posts": len(posts),
                "total_comments": len(comments),
            },
        )
