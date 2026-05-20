from typing import Any

from pydantic import BaseModel, Field


class CollectorConfig(BaseModel):
    """采集器通用配置 - 当前阶段仅支持 media_crawler"""

    collector_type: str = Field(
        default="media_crawler",
        description="采集器类型: media_crawler, xhs_sdk",
    )
    mode: str = Field(
        default="test", description="模式: test（测试）/ real（真实）"
    )
    max_posts: int = Field(default=10, ge=1, le=1000, description="单次采集最多笔记数")
    max_comments_per_post: int = Field(
        default=50, ge=1, le=100, description="每条笔记最多评论数"
    )
    timeout_seconds: int = Field(
        default=30, ge=5, le=300, description="请求超时时间（秒）"
    )
    retry_times: int = Field(default=3, ge=1, le=10, description="重试次数")
    rate_limit_seconds: int = Field(
        default=1, ge=0, le=60, description="请求间隔（秒），避免频率过高"
    )
    cookies: str | None = Field(
        default=None, description="登录 Cookie（小红书/抖音等平台使用）"
    )
    user_agent: str | None = Field(default=None, description="自定义 UA")
    login_type: str | None = Field(
        default=None,
        description="MediaCrawler 登录方式: cookie/qrcode/phone",
    )
    enable_comments: bool | None = Field(
        default=None,
        description="MediaCrawler 是否采集评论（默认 True）",
    )
    time_range: str | None = Field(
        default=None,
        description="采集时间范围: 7d/15d/30d/90d，为空则不限制",
    )

    TIME_RANGE_DAYS: dict[str, int] = {
        "7d": 7,
        "15d": 15,
        "30d": 30,
        "90d": 90,
    }

    TIME_RANGE_BOOSTED_MAX_POSTS: int = 80

    def get_time_range_days(self) -> int | None:
        if not self.time_range:
            return None
        return self.TIME_RANGE_DAYS.get(self.time_range)

    def get_effective_max_posts(self) -> int:
        if self.get_time_range_days() is not None:
            return max(self.max_posts, self.TIME_RANGE_BOOSTED_MAX_POSTS)
        return self.max_posts

    class Config:
        extra = "allow"

    @staticmethod
    def parse(config: Any | None) -> "CollectorConfig":
        if config is None:
            return CollectorConfig()
        if isinstance(config, CollectorConfig):
            return config
        if isinstance(config, dict):
            return CollectorConfig(**config)
        if hasattr(config, "__dict__"):
            return CollectorConfig(**config.__dict__)
        return CollectorConfig()

    def validate_collector_type(self) -> tuple[bool, str]:
        """校验采集器类型是否支持"""
        supported_types = {"media_crawler", "xhs_sdk"}
        if self.collector_type not in supported_types:
            return False, (
                f"Unsupported collector_type: {self.collector_type}. "
                "Supported types: media_crawler, xhs_sdk"
            )
        return True, ""

    def validate_for_collector_type(self) -> tuple[bool, str]:
        """针对不同采集器类型的具体校验"""
        if self.collector_type == "media_crawler":
            login_type = (self.login_type or "cookie").strip().lower()
            if login_type not in {"cookie", "qrcode", "phone"}:
                return False, f"login_type must be one of cookie/qrcode/phone, got {login_type}"
        return True, ""
