import asyncio
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

from app.collectors.base import BaseCollector, CollectedComment, CollectedPost, CollectorResult


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
        now = datetime.now(timezone.utc)

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
                    await page.wait_for_timeout(1200)

                    title = await self._extract_text(page, [
                        "h1",
                        "article h1",
                        "[data-testid='title']",
                        ".title",
                    ])
                    content = await self._extract_text(page, [
                        "article",
                        "main article",
                        "[data-testid='content']",
                        ".content",
                    ])
                    author = await self._extract_text(page, [
                        "[data-testid='author']",
                        "[rel='author']",
                        ".author",
                        ".user-name",
                    ])

                    await self._scroll_comments(page)
                    comment_texts = await self._extract_comments(page)

                    post_key = source_url.encode("utf-8")
                    post_id = f"manual-{sha1(post_key).hexdigest()[:16]}"
                    post = CollectedPost(
                        platform=platform,
                        post_id=post_id,
                        title=title,
                        content=content,
                        post_url=source_url,
                        author_name=author,
                        comment_count=len(comment_texts),
                        publish_time=now,
                        raw_data={
                            "collector": "playwright",
                            "source_url": source_url,
                            "browser_channel": launch_channel,
                        },
                    )

                    comments = [
                        CollectedComment(
                            platform=platform,
                            post_id=post_id,
                            comment_id=f"{post_id}-c-{index + 1}",
                            content=text,
                            publish_time=now,
                            raw_data={
                                "collector": "playwright",
                                "source_url": source_url,
                                "browser_channel": launch_channel,
                            },
                        )
                        for index, text in enumerate(comment_texts)
                    ]

                    return CollectorResult(posts=[post], comments=comments)
                except PlaywrightTimeoutError as error:
                    raise RuntimeError(f"playwright timeout when loading or extracting page: {error}") from error
                except Exception as error:
                    raise RuntimeError(f"playwright collect failed: {error}") from error
                finally:
                    await context.close()
                    await browser.close()
        except Exception:
            raise

    async def _extract_text(self, page: Any, selectors: list[str]) -> str | None:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue
                text = (await locator.inner_text()).strip()
                if text:
                    return text[:2000]
            except Exception:
                continue
        return None

    async def _scroll_comments(self, page: Any) -> None:
        for _ in range(6):
            try:
                await page.mouse.wheel(0, 1600)
                await page.wait_for_timeout(500)
            except Exception:
                break

    async def _extract_comments(self, page: Any) -> list[str]:
        selectors = [
            "[data-testid='comment']",
            ".comment-item",
            ".comment",
            "[class*='comment']",
        ]
        comments: list[str] = []
        seen: set[str] = set()

        for selector in selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count == 0:
                    continue
                limit = min(count, 100)
                for index in range(limit):
                    raw_text = await elements.nth(index).inner_text()
                    text = (raw_text or "").strip()
                    if not text:
                        continue
                    text = text.replace("\n", " ")
                    if text in seen:
                        continue
                    seen.add(text)
                    comments.append(text[:1000])
                if comments:
                    break
            except Exception:
                continue

        return comments
