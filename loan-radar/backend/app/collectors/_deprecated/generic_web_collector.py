"""通用网页采集器 - 支持 CSS 选择器的网页采集"""

import asyncio
from typing import Any

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.config import CollectorConfig
from app.collectors.page_parsers.factory import PageParserFactory


class GenericWebCollector(BaseCollector):
    """
    通用网页采集器 - 支持 CSS 选择器的网页内容提取

    特点:
    - 使用 Playwright 加载网页
    - 支持自定义 CSS 选择器映射
    - 支持动态渲染页面
    - 支持等待动态内容加载
    """

    def collect(self, source: Any) -> CollectorResult:
        """
        采集网页数据

        Args:
            source: 监控源对象，应有 config 属性（包含 entry_url 和 selectors）

        Returns:
            CollectorResult: 包含 posts、comments、metadata 的结果

        Raises:
            ValueError: 配置错误
        """
        config = getattr(source, "config", None) or {}
        config_obj = CollectorConfig.parse(config)
        platform = getattr(source, "platform", "generic_web")

        # 验证配置
        is_valid, msg = config_obj.validate_for_collector_type()
        if not is_valid:
            raise ValueError(f"Invalid generic_web config: {msg}")

        # 获取 URL 和选择器
        entry_url = config_obj.entry_url
        selectors = config_obj.selectors or {}

        if not entry_url:
            raise ValueError("entry_url is required for generic_web collector")
        if not entry_url.startswith("http://") and not entry_url.startswith("https://"):
            raise ValueError("entry_url must start with http:// or https://")

        try:
            return asyncio.run(
                self._collect_async(
                    source_url=entry_url,
                    platform=platform,
                    selectors=selectors,
                    timeout_seconds=config_obj.timeout_seconds,
                    max_posts=config_obj.max_posts,
                    max_comments_per_post=config_obj.max_comments_per_post,
                )
            )
        except RuntimeError as error:
            # 允许在嵌套事件循环环境中运行协程
            if "asyncio.run() cannot be called" in str(error):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(
                        self._collect_async(
                            source_url=entry_url,
                            platform=platform,
                            selectors=selectors,
                            timeout_seconds=config_obj.timeout_seconds,
                            max_posts=config_obj.max_posts,
                            max_comments_per_post=config_obj.max_comments_per_post,
                        )
                    )
                finally:
                    loop.close()
            raise

    async def _collect_async(
        self,
        source_url: str,
        platform: str,
        selectors: dict[str, str],
        timeout_seconds: int,
        max_posts: int,
        max_comments_per_post: int,
    ) -> CollectorResult:
        """
        异步采集网页数据

        Args:
            source_url: 网页 URL
            platform: 平台名称
            selectors: CSS 选择器映射
            timeout_seconds: 超时时间
            max_posts: 最大笔记数
            max_comments_per_post: 每条笔记的最大评论数

        Returns:
            CollectorResult
        """
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise RuntimeError(
                "playwright is not installed, please install package and browser binaries"
            ) from error

        timeout_ms = timeout_seconds * 1000
        wait_after_load_ms = 2000

        try:
            async with async_playwright() as playwright:
                # 选择浏览器
                launch_channel = "chromium"
                try:
                    browser = await playwright.chromium.launch(headless=True)
                except Exception:
                    # 尝试使用本地 Edge 浏览器
                    try:
                        browser = await playwright.chromium.launch(channel="msedge", headless=True)
                        launch_channel = "msedge"
                    except Exception:
                        # 最后尝试 Chrome
                        browser = await playwright.chromium.launch(channel="chrome", headless=True)
                        launch_channel = "chrome"

                context = await browser.new_context()
                page = await context.new_page()
                page.set_default_timeout(timeout_ms)

                try:
                    # 加载页面
                    await page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    await page.wait_for_timeout(wait_after_load_ms)

                    # 使用 GenericPageParser 解析页面
                    from app.collectors.page_parsers.generic import GenericPageParser

                    parser = GenericPageParser()
                    return await parser.parse(
                        page=page,
                        source_url=source_url,
                        platform=platform,
                        browser_channel=launch_channel,
                        selectors=selectors,
                        max_posts=max_posts,
                        max_comments_per_post=max_comments_per_post,
                    )

                except PlaywrightTimeoutError as error:
                    raise RuntimeError(f"page load timeout: {error}") from error
                except Exception as error:
                    raise RuntimeError(f"generic_web collect failed: {error}") from error
                finally:
                    await context.close()
                    await browser.close()

        except Exception:
            raise
