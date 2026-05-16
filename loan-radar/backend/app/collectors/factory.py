import os
from pathlib import Path
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.config import CollectorConfig
from app.collectors.media_crawler.collector import MediaCrawlerCollector
from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS as MC_PLATFORMS


def _is_embedded_mode() -> bool:
    home = os.getenv("MEDIA_CRAWLER_HOME")
    if not home:
        return False
    p = Path(home)
    if not p.is_absolute():
        p = Path(os.getcwd()) / home
    return p.is_dir()


class CollectorFactory:
    """采集器工厂 - 根据 collector_type 严格路由

    当设置了 MEDIA_CRAWLER_HOME 环境变量时，优先使用 EmbeddedMediaCrawlerCollector
    （直接调用 MediaCrawler Python API，无需单独启动 HTTP 服务）。
    否则使用 MediaCrawlerCollector（通过 HTTP bridge 调用 MediaCrawler API 服务）。
    """

    @staticmethod
    def create(source: Any) -> BaseCollector:
        config = getattr(source, "config", None) or {}
        config_obj = CollectorConfig.parse(config)
        is_valid, msg = config_obj.validate_collector_type()
        if not is_valid:
            raise ValueError(msg)

        if config_obj.collector_type == "media_crawler":
            if _is_embedded_mode():
                try:
                    from app.collectors.media_crawler.embedded_collector import (
                        EmbeddedMediaCrawlerCollector,
                    )
                    return EmbeddedMediaCrawlerCollector()
                except Exception:
                    pass
            return MediaCrawlerCollector()

        raise ValueError(f"Unsupported collector_type: {config_obj.collector_type}")

    @staticmethod
    def get_supported_collectors() -> dict[str, dict[str, Any]]:
        mc_platforms = sorted(MC_PLATFORMS)
        mode = "embedded" if _is_embedded_mode() else "http_bridge"
        return {
            "media_crawler": {
                "name": "MediaCrawler 多平台采集器",
                "description": (
                    f"基于 MediaCrawler 开源项目，支持多平台采集："
                    f"{', '.join(mc_platforms)}。"
                    "支持关键词搜索、指定帖子、创作者主页采集。"
                ),
                "status": "ready",
                "mode": mode,
                "supports": ["keyword", "competitor_account", "manual_post", "hot_post_rule"],
                "config": {
                    "collector_type": "media_crawler",
                    "login_type": "cookie",
                    "enable_comments": True,
                    "max_posts": 20,
                    "max_comments_per_post": 50,
                },
            },
        }
