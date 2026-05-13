from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlparse

from app.collectors.base import CollectionAuthError, CollectionRequestError


def sanitize_cdp_error(message: str) -> str:
    sanitized = message
    sanitized = re.sub(
        r"(cookie|token|api[_-]?key|authorization|session|web_session)\s*[:=]\s*[^\s,;&]+",
        r"\1=***",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"([?&](cookie|token|api_key|apikey|auth|authorization|session|web_session)=)[^&\s]+",
        r"\1***",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def _run_async(coro: Any) -> Any:
    try:
        return asyncio.run(coro)
    except RuntimeError as error:
        if "asyncio.run() cannot be called" not in str(error):
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class XhsCdpClient:
    def __init__(
        self,
        endpoint: str | None = None,
        timeout: float = 20.0,
        browser_channel: str | None = None,
    ) -> None:
        self.endpoint = (endpoint or os.getenv("XHS_CDP_ENDPOINT") or "http://127.0.0.1:9222").strip()
        self.timeout_ms = int(max(1.0, timeout) * 1000)
        self.browser_channel = (browser_channel or os.getenv("XHS_CDP_BROWSER_CHANNEL") or "").strip() or None

    def close(self) -> None:
        return None

    def search_notes(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        return _run_async(self._search_notes(keyword=keyword, limit=limit))

    def get_note_detail(self, post_url: str) -> dict[str, Any]:
        return _run_async(self._get_note_detail(post_url=post_url))

    def get_note_comments(
        self,
        post_id: str,
        post_url: str,
        xsec_token: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        _ = xsec_token
        return _run_async(self._get_note_comments(post_id=post_id, post_url=post_url, limit=limit))

    async def _with_cdp_page(self, url: str, callback: Any) -> Any:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise CollectionRequestError("playwright is required for xhs cdp collection") from error

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.connect_over_cdp(self.endpoint, timeout=self.timeout_ms)
                try:
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                    page = await context.new_page()
                    page.set_default_timeout(self.timeout_ms)
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                        await page.wait_for_timeout(1500)
                        await self._ensure_logged_in(page)
                        return await callback(page)
                    finally:
                        await page.close()
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as error:
            raise CollectionRequestError(f"xhs cdp page load timeout: {sanitize_cdp_error(str(error))}") from error
        except CollectionAuthError:
            raise
        except CollectionRequestError:
            raise
        except Exception as error:
            raise CollectionRequestError(f"xhs cdp request failed: {sanitize_cdp_error(str(error))}") from error

    async def _ensure_logged_in(self, page: Any) -> None:
        current_url = page.url.lower()
        content = ""
        try:
            content = (await page.locator("body").inner_text(timeout=3000)).lower()
        except Exception:
            content = ""

        auth_tokens = ("登录", "login", "验证码", "安全验证", "请完成验证")
        if any(token in current_url for token in ("login", "captcha")):
            raise CollectionAuthError("xhs cdp browser is not logged in or is blocked by verification")
        if any(token in content for token in auth_tokens) and not await self._has_note_content(page):
            raise CollectionAuthError("xhs cdp browser is not logged in or is blocked by verification")

    async def _has_note_content(self, page: Any) -> bool:
        for selector in ("a[href*='/explore/']", "section.note-content", "div[class*='note-content']"):
            try:
                if await page.locator(selector).count() > 0:
                    return True
            except Exception:
                continue
        return False

    async def _search_notes(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        bounded_limit = max(1, limit)
        url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}&source=web_search_result_notes"

        async def collect(page: Any) -> list[dict[str, Any]]:
            for _ in range(3):
                if await page.locator("a[href*='/explore/']").count() >= bounded_limit:
                    break
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(1000)
            return await self._extract_note_cards(page=page, limit=bounded_limit)

        return await self._with_cdp_page(url, collect)

    async def _get_note_detail(self, post_url: str) -> dict[str, Any]:
        async def collect(page: Any) -> dict[str, Any]:
            note_id = self._note_id_from_url(post_url)
            payload = await self._extract_detail(page=page, post_url=post_url, note_id=note_id)
            if not payload.get("id") and not payload.get("note_id"):
                raise CollectionRequestError("xhs cdp note detail format is invalid")
            return payload

        return await self._with_cdp_page(post_url, collect)

    async def _get_note_comments(self, post_id: str, post_url: str, limit: int) -> list[dict[str, Any]]:
        async def collect(page: Any) -> list[dict[str, Any]]:
            comments = await self._extract_comments(page=page, post_id=post_id, limit=max(1, limit))
            return comments

        return await self._with_cdp_page(post_url, collect)

    async def _extract_note_cards(self, page: Any, limit: int) -> list[dict[str, Any]]:
        script = """
        (limit) => {
          const seen = new Set();
          const cards = [];
          const anchors = Array.from(document.querySelectorAll("a[href*='/explore/']"));
          for (const anchor of anchors) {
            const href = anchor.href || anchor.getAttribute("href") || "";
            const match = href.match(/\\/explore\\/([^/?#]+)/);
            if (!match || seen.has(match[1])) continue;
            seen.add(match[1]);
            const root = anchor.closest("section, article, div") || anchor;
            const text = (root.innerText || anchor.innerText || "").trim();
            const lines = text.split(/\\n+/).map((line) => line.trim()).filter(Boolean);
            const title = lines[0] || anchor.getAttribute("title") || "";
            const author = lines.find((line) => line.length > 0 && line !== title) || "";
            cards.push({
              id: match[1],
              url: href,
              note_card: {
                note_id: match[1],
                title,
                desc: lines.slice(1, 5).join("\\n"),
                user: author ? { nickname: author } : {}
              }
            });
            if (cards.length >= limit) break;
          }
          return cards;
        }
        """
        data = await page.evaluate(script, limit)
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    async def _extract_detail(self, page: Any, post_url: str, note_id: str) -> dict[str, Any]:
        script = """
        () => {
          const pickText = (selectors) => {
            for (const selector of selectors) {
              const el = document.querySelector(selector);
              const text = el && (el.innerText || el.textContent || "").trim();
              if (text) return text;
            }
            return "";
          };
          const title = pickText(["#detail-title", "h1", "div[class*='title']", "span[class*='title']"]);
          const desc = pickText(["#detail-desc", "div[class*='desc']", "div[class*='content']", "article"]);
          const author = pickText(["a[href*='/user/profile/']", "span[class*='author']", "div[class*='author']", ".name"]);
          const likeText = pickText(["span[class*='like']", "div[class*='like']"]);
          const commentText = pickText(["span[class*='comment']", "div[class*='comment']"]);
          return { title, desc, author, likeText, commentText, bodyText: (document.body.innerText || "").slice(0, 3000) };
        }
        """
        data = await page.evaluate(script)
        title = str(data.get("title") or "").strip() if isinstance(data, dict) else ""
        desc = str(data.get("desc") or "").strip() if isinstance(data, dict) else ""
        author = str(data.get("author") or "").strip() if isinstance(data, dict) else ""

        return {
            "id": note_id,
            "url": post_url,
            "note_card": {
                "note_id": note_id,
                "title": title,
                "desc": desc,
                "user": {"nickname": author} if author else {},
                "time": datetime.now(UTC).isoformat(),
            },
            "cdp_metadata": {
                "endpoint": self.endpoint,
                "browser_channel": self.browser_channel,
                "source": "cdp",
            },
        }

    async def _extract_comments(self, page: Any, post_id: str, limit: int) -> list[dict[str, Any]]:
        script = """
        (limit) => {
          const nodes = Array.from(document.querySelectorAll("div[class*='comment'], .comment-item, [data-testid*='comment']"));
          const seen = new Set();
          const comments = [];
          for (const node of nodes) {
            const text = (node.innerText || node.textContent || "").trim().replace(/\\n+/g, " ");
            if (!text || text.length < 2 || seen.has(text)) continue;
            seen.add(text);
            comments.push({ content: text.slice(0, 1000) });
            if (comments.length >= limit) break;
          }
          return comments;
        }
        """
        data = await page.evaluate(script, limit)
        if not isinstance(data, list):
            return []
        comments: list[dict[str, Any]] = []
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            comments.append(
                {
                    "id": f"{post_id}-cdp-{index}",
                    "note_id": post_id,
                    "content": content,
                    "create_time": datetime.now(UTC).isoformat(),
                }
            )
        return comments

    def _note_id_from_url(self, post_url: str) -> str:
        parsed = urlparse(post_url)
        note_id = parsed.path.rstrip("/").split("/")[-1]
        if not note_id:
            raise CollectionRequestError("invalid xhs post url")
        return note_id
