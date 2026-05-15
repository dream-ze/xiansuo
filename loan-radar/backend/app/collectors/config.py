"""采集器配置解析和校验工具"""

from typing import Any

from pydantic import BaseModel, Field


class CollectorConfig(BaseModel):
    """采集器通用配置"""

    collector_type: str = Field(
        default="media_crawler",
        description="采集器类型: media_crawler",
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
    entry_url: str | None = Field(
        default=None, description="网页入口 URL（generic_web 使用）"
    )
    selectors: dict[str, str] | None = Field(
        default=None,
        description="CSS 选择器映射: {title, content, author, comment_item, ...}",
    )
    external_api: dict[str, Any] | None = Field(
        default=None,
        description="外部 API 配置: {endpoint, api_key_env, request_timeout}",
    )
    cookies: str | None = Field(
        default=None, description="登录 Cookie（小红书/抖音等平台使用）"
    )
    proxies: str | None = Field(default=None, description="代理地址: http://ip:port")
    user_agent: str | None = Field(default=None, description="自定义 UA")
    login_type: str | None = Field(
        default=None,
        description="MediaCrawler 登录方式: cookie/qrcode/phone",
    )
    enable_comments: bool | None = Field(
        default=None,
        description="MediaCrawler 是否采集评论（默认 True）",
    )

    class Config:
        extra = "allow"

    @staticmethod
    def parse(config: Any | None) -> "CollectorConfig":
        """从任意配置对象解析为 CollectorConfig"""
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
        supported_types = {"media_crawler"}
        if self.collector_type not in supported_types:
            return False, f"Unsupported collector_type: {self.collector_type}"
        return True, ""

    def validate_for_collector_type(self) -> tuple[bool, str]:
        """针对不同采集器类型的具体校验"""
        if self.collector_type == "media_crawler":
            login_type = (self.login_type or "cookie").strip().lower()
            if login_type not in {"cookie", "qrcode", "phone"}:
                return False, f"login_type must be one of cookie/qrcode/phone, got {login_type}"
        return True, ""
