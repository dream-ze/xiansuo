"""小红书采集器 - 采集小红书笔记和评论"""

import asyncio
from typing import Any

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.config import CollectorConfig
from app.collectors.page_parsers.xhs import XhsPageParser


class XhsCollector(BaseCollector):
    """
    小红书采集器 - 使用 Playwright 采集小红书页面内容
    
    特点：
    - 支持 cookie 认证
    - 支持自定义 CSS 选择器
    - 支持浏览器回退机制
    - 处理反爬虫措施
    """

    def __init__(self):
        pass

    def collect(self, source: Any) -> CollectorResult:
        """
        采集小红书页面内容

        Args:
            source: 监控源对象，应有 config 属性

        Returns:
            CollectorResult: 包含 posts、comments、metadata 的结果

        Raises:
            ValueError: 配置错误
            RuntimeError: 采集过程中的错误
        """
        config = getattr(source, "config", None) or {}
        config_obj = CollectorConfig.parse(config)
        platform = getattr(source, "platform", "xhs")
        source_url = getattr(source, "value", "") or ""

        # 验证配置
        is_valid, msg = config_obj.validate_for_collector_type()
        if not is_valid:
            raise ValueError(f"Invalid xhs config: {msg}")

        # 验证 URL
        if not source_url:
            raise ValueError("xhs source.value (entry URL) is required")
        if not source_url.startswith("http://") and not source_url.startswith("https://"):
            raise ValueError("xhs source.value must be a valid http/https URL")

        # 获取 cookie
        cookies = config_obj.cookies
        if not cookies:
            raise ValueError("xhs requires cookies for authentication")

        try:
            return asyncio.run(self._collect_async(
                source=source,
                source_url=source_url,
                platform=platform,
                cookies=cookies,
                config_obj=config_obj,
            ))
        except RuntimeError as error:
            # 允许嵌套事件循环环境运行协程
            if "asyncio.run() cannot be called" in str(error):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(self._collect_async(
                        source=source,
                        source_url=source_url,
                        platform=platform,
                        cookies=cookies,
                        config_obj=config_obj,
                    ))
                finally:
                    loop.close()
            raise

    async def _collect_async(
        self,
        source: Any,
        source_url: str,
        platform: str,
        cookies: str,
        config_obj: CollectorConfig,
    ) -> CollectorResult:
        """异步采集小红书页面"""
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise RuntimeError(
                "playwright is not installed, please install package and browser binaries"
            ) from error

        timeout_ms = config_obj.timeout_seconds * 1000
        wait_after_load_ms = 2000  # 小红书需要更多时间加载动态内容
        max_posts = config_obj.max_posts
        max_comments_per_post = config_obj.max_comments_per_post
        
        # 解析自定义选择器
        selectors = None
        if isinstance(config_obj.selectors, dict) and config_obj.selectors:
            selectors = config_obj.selectors

        try:
            async with async_playwright() as playwright:
                # 尝试浏览器回退：chromium → msedge → chrome
                browser = None
                launch_channel = None
                browsers_to_try = [
                    ("chromium", None),
                    ("chromium", "msedge"),
                    ("chromium", "chrome"),
                ]

                for browser_type_name, channel in browsers_to_try:
                    try:
                        if channel:
                            browser = await getattr(
                                playwright, browser_type_name
                            ).launch(channel=channel, headless=True)
                            launch_channel = channel
                        else:
                            browser = await getattr(
                                playwright, browser_type_name
                            ).launch(headless=True)
                            launch_channel = browser_type_name
                        break
                    except Exception:
                        continue

                if not browser:
                    raise RuntimeError("Failed to launch any browser for xhs collection")

                try:
                    context = await browser.new_context()
                    
                    # 设置 cookie
                    await self._set_cookies(context, cookies, source_url)
                    
                    page = await context.new_page()
                    page.set_default_timeout(timeout_ms)

                    try:
                        await page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                        await page.wait_for_timeout(wait_after_load_ms)
                        
                        parser = XhsPageParser(
                            platform=platform,
                            max_comments_per_post=max_comments_per_post,
                            selectors=selectors,
                            max_posts=max_posts,
                        )
                        
                        return await parser.parse(
                            page=page,
                            source_url=source_url,
                            platform=platform,
                            browser_channel=launch_channel,
                            cookies=cookies,
                            max_posts=max_posts,
                            max_comments_per_post=max_comments_per_post,
                        )
                    except PlaywrightTimeoutError as error:
                        raise RuntimeError(f"xhs page load timeout: {error}") from error
                    except Exception as error:
                        raise RuntimeError(f"xhs collect failed: {error}") from error
                    finally:
                        await context.close()
                        await browser.close()
                except Exception:
                    raise
        except Exception:
            raise

    async def _set_cookies(self, context: Any, cookies_str: str, url: str) -> None:
        """
        设置 cookie 到浏览器上下文
        
        Args:
            context: Playwright 浏览器上下文
            cookies_str: Cookie 字符串（支持多种格式）
            url: 目标 URL
        """
        if not cookies_str:
            return

        try:
            # 尝试解析 JSON 格式的 cookie
            import json
            
            try:
                cookies_list = json.loads(cookies_str)
                if isinstance(cookies_list, list):
                    await context.add_cookies(cookies_list)
                    return
            except (json.JSONDecodeError, ValueError):
                pass

            # 处理 Set-Cookie 格式或原始 cookie 字符串
            cookies_list = []
            for cookie_part in cookies_str.split(";"):
                cookie_part = cookie_part.strip()
                if not cookie_part or "=" not in cookie_part:
                    continue

                key, value = cookie_part.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 移除常见的 cookie 属性
                if key.lower() in ["path", "domain", "expires", "max-age", "secure", "httponly", "samesite"]:
                    continue

                cookies_list.append({
                    "name": key,
                    "value": value,
                    "url": url,
                })

            if cookies_list:
                await context.add_cookies(cookies_list)

        except Exception:
            # 如果设置 cookie 失败，继续进行采集（可能页面可以无认证访问）
            pass
