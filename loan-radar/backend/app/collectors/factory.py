from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.config import CollectorConfig
from app.collectors.external_api_collector import ExternalApiCollector
from app.collectors.generic_web_collector import GenericWebCollector
from app.collectors.mock_collector import MockCollector
from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.xhs_collector import XhsCollector


class CollectorFactory:
    """采集器工厂 - 根据 collector_type 严格路由"""

    @staticmethod
    def create(source: Any) -> BaseCollector:
        """
        根据 source.config.collector_type 和 source.source_type 创建对应采集器

        Args:
            source: 监控源对象，应有 source_type、platform、config 属性

        Returns:
            BaseCollector 实例

        Raises:
            ValueError: collector_type 不支持或参数组合非法
        """
        config = getattr(source, "config", None) or {}
        config_obj = CollectorConfig.parse(config)
        source_type = getattr(source, "source_type", "")
        platform = getattr(source, "platform", "")

        # 验证 collector_type 是否支持
        is_valid, msg = config_obj.validate_collector_type()
        if not is_valid:
            raise ValueError(msg)

        # 严格路由
        if config_obj.collector_type == "mock":
            return MockCollector()

        elif config_obj.collector_type == "playwright":
            # Playwright 只支持 manual_post
            if source_type != "manual_post":
                raise ValueError(
                    f"playwright collector only supports manual_post source_type, got {source_type}"
                )
            return PlaywrightCollector()

        elif config_obj.collector_type == "xhs":
            # Phase 5 实现
            return XhsCollector()

        elif config_obj.collector_type == "douyin":
            raise NotImplementedError(
                "douyin collector will be implemented in Phase 6. "
                "Please use external_api or mock."
            )

        elif config_obj.collector_type == "zhihu":
            raise NotImplementedError(
                "zhihu collector will be implemented in Phase 6. "
                "Please use external_api or mock."
            )

        elif config_obj.collector_type == "generic_web":
            return GenericWebCollector()

        elif config_obj.collector_type == "external_api":
            return ExternalApiCollector()

        else:
            # 这里不应该到达，因为 validate_collector_type 已检查
            raise ValueError(f"Unknown collector_type: {config_obj.collector_type}")

    @staticmethod
    def get_supported_collectors() -> dict[str, dict[str, Any]]:
        """获取所有支持的采集器能力列表"""
        return {
            "mock": {
                "name": "Mock Collector",
                "description": "测试/演示用 Mock 采集器，生成模拟数据",
                "status": "ready",
                "supports": ["keyword", "competitor_account", "manual_post", "hot_post_rule"],
                "config": {
                    "collector_type": "mock",
                    "mode": "test",
                    "max_posts": 10,
                    "max_comments_per_post": 50,
                },
            },
            "playwright": {
                "name": "Playwright Collector",
                "description": "通过 Playwright 采集公开网页链接的内容",
                "status": "ready",
                "supports": ["manual_post"],
                "config": {
                    "collector_type": "playwright",
                    "max_comments_per_post": 50,
                    "timeout_seconds": 30,
                },
            },
            "xhs": {
                "name": "Xiaohongshu (小红书) Collector",
                "description": "小红书平台采集器，支持笔记抓取和评论采集",
                "status": "ready",  # Phase 5 实现
                "supports": ["keyword", "competitor_account", "manual_post"],
                "config": {
                    "collector_type": "xhs",
                    "cookies": "required",
                    "entry_url": "https://www.xiaohongshu.com/",
                    "selectors": {"note_container": "div[class*='feed-item']"},
                    "max_posts": 20,
                    "max_comments_per_post": 50,
                },
            },
            "douyin": {
                "name": "Douyin (抖音) Collector",
                "description": "抖音平台采集器，支持关键词搜索和用户视频抓取",
                "status": "planned",  # Phase 6 规划
                "supports": ["keyword", "competitor_account"],
                "config": {
                    "collector_type": "douyin",
                    "cookies": "optional",
                    "max_posts": 20,
                },
            },
            "zhihu": {
                "name": "Zhihu (知乎) Collector",
                "description": "知乎平台采集器，支持话题和问题采集",
                "status": "planned",  # Phase 6 规划
                "supports": ["keyword", "competitor_account"],
                "config": {
                    "collector_type": "zhihu",
                    "max_posts": 20,
                },
            },
            "external_api": {
                "name": "External API Collector",
                "description": "通过外部第三方 API 接入真实采集数据",
                "status": "ready",  # Phase 3 实现完成
                "supports": ["keyword", "competitor_account"],
                "config": {
                    "collector_type": "external_api",
                    "external_api": {
                        "endpoint": "https://your-api.com/collect",
                        "api_key_env": "YOUR_API_KEY",
                    },
                },
            },
            "generic_web": {
                "name": "Generic Web Collector",
                "description": "通用网页采集器，支持自定义 CSS 选择器",
                "status": "ready",  # Phase 4 实现完成
                "supports": ["manual_post", "keyword"],
                "config": {
                    "collector_type": "generic_web",
                    "entry_url": "https://example.com/page",
                    "selectors": {
                        "post_container": "article, .post",
                        "title": "h1, h2",
                        "content": "article, .content",
                        "author": ".author",
                        "comment_item": ".comment",
                    },
                    "max_posts": 10,
                    "max_comments_per_post": 50,
                },
            },
        }

