from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.config import CollectorConfig
from app.collectors.media_crawler.collector import MediaCrawlerCollector
from app.collectors.media_crawler.mappers import SUPPORTED_PLATFORMS as MC_PLATFORMS


class CollectorFactory:
    """采集器工厂 - 根据 collector_type 严格路由"""

    @staticmethod
    def create(source: Any) -> BaseCollector:
        config = getattr(source, "config", None) or {}
        config_obj = CollectorConfig.parse(config)
        is_valid, msg = config_obj.validate_collector_type()
        if not is_valid:
            raise ValueError(msg)

        if config_obj.collector_type == "media_crawler":
            return MediaCrawlerCollector()

        raise ValueError(f"Unsupported collector_type: {config_obj.collector_type}")

    @staticmethod
    def get_supported_collectors() -> dict[str, dict[str, Any]]:
        """获取所有支持的采集器能力列表"""
        mc_platforms = sorted(MC_PLATFORMS)
        return {
            "media_crawler": {
                "name": "MediaCrawler 多平台采集器",
                "description": (
                    f"基于 MediaCrawler 开源项目，支持多平台采集："
                    f"{', '.join(mc_platforms)}。"
                    "支持关键词搜索、指定帖子、创作者主页采集。"
                    "需启动 MediaCrawler API 服务或配置 MEDIA_CRAWLER_HOME。"
                ),
                "status": "ready",
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
