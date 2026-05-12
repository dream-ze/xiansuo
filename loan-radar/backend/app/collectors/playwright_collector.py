import asyncio
from typing import Any

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.page_parsers.factory import PageParserFactory


class PlaywrightCollector(BaseCollector):
    def collect(self, source: Any) -> CollectorResult:
        source_url = (getattr(source, "value", "") or "").strip()
        if not source_url:
            raise ValueError("manual_post source.value is empty")
        if not source_url.startswith("http://") and not source_url.startswith("https://"):
            raise ValueError("manual_post source.value must be a valid http/https URL")

        try:
            return asyncio.run(self._collect_async(source, source_url))
        except RuntimeError as error:
            # Allow nested event-loop environments to run the coroutine safely.
            if "asyncio.run() cannot be called" in str(error):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(self._collect_async(source, source_url))
                finally:
                    loop.close()
            raise

    async def _collect_async(self, source: Any, source_url: str) -> CollectorResult:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise RuntimeError("playwright is not installed, please install package and browser binaries") from error

        timeout_ms = 15_000
        platform = getattr(source, "platform", "other")
        config = getattr(source, "config", None) or {}
        if isinstance(config, dict):
            timeout_ms = int(config.get("timeout_ms") or timeout_ms)
            wait_after_load_ms = int(config.get("wait_after_load_ms") or 1200)
            max_comments_per_post = int(config.get("max_comments_per_post") or 50)
        else:
            wait_after_load_ms = 1200
            max_comments_per_post = 50

        try:
            async with async_playwright() as playwright:
                launch_channel = "chromium"
                try:
                    browser = await playwright.chromium.launch(headless=True)
                except Exception as launch_error:
                    # In restricted networks, bundled Chromium may fail to install.
                    # Fall back to local Edge channel to keep manual_post experiment usable.
                    browser = await playwright.chromium.launch(channel="msedge", headless=True)
                    launch_channel = "msedge"

                context = await browser.new_context()
                page = await context.new_page()
                page.set_default_timeout(timeout_ms)

                try:
                    await page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    await page.wait_for_timeout(wait_after_load_ms)
                    parser = PageParserFactory.create(
                        platform=platform,
                        max_comments_per_post=max_comments_per_post,
                    )
                    return await parser.parse(
                        page=page,
                        source_url=source_url,
                        platform=platform,
                        browser_channel=launch_channel,
                    )
                except PlaywrightTimeoutError as error:
                    raise RuntimeError(f"page load timeout: {error}") from error
                except Exception as error:
                    raise RuntimeError(f"playwright collect failed: {error}") from error
                finally:
                    await context.close()
                    await browser.close()
        except Exception:
            raise
