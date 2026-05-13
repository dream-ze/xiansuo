from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import threading
import time
from typing import Any

from app.collectors.base import CollectionAuthError, CollectionRequestError

logger = logging.getLogger(__name__)

_XHS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)


class XhsBrowserSigner:
    _instance: XhsBrowserSigner | None = None
    _init_lock = threading.Lock()

    def __init__(self, state_dir: str | None = None, headless: bool = True) -> None:
        self.state_dir = state_dir or os.path.join(
            os.getenv("XHS_BROWSER_STATE_DIR") or os.path.join(os.getcwd(), ".browser_state"),
        )
        self.headless = headless
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._started = False
        self._logged_in = False
        self._sign_available = False
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> XhsBrowserSigner:
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._init_lock:
            if cls._instance is not None:
                try:
                    cls._instance.close()
                except Exception:
                    pass
                cls._instance = None

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and self._loop.is_running():
            return self._loop
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        for _ in range(200):
            if self._loop is not None and self._loop.is_running():
                return self._loop
            time.sleep(0.05)
        raise RuntimeError("Failed to start browser event loop")

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _submit(self, coro: Any, timeout: float = 60.0) -> Any:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)

    async def _start_browser(self) -> None:
        if self._started and self._page and not self._page.is_closed():
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise CollectionRequestError(
                "playwright is required for xhs browser signing. "
                "Install with: pip install playwright && playwright install"
            ) from error

        self._playwright = await async_playwright().start()

        state_file = os.path.join(self.state_dir, "xhs_state.json")
        storage_state = state_file if os.path.exists(state_file) else None

        if storage_state:
            logger.info("Loading saved browser state from %s", state_file)

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        self._context = await self._browser.new_context(
            storage_state=storage_state,
            user_agent=_XHS_USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )

        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        self._page = await self._context.new_page()
        self._page.set_default_timeout(60000)

        await self._page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=60000)
        await self._page.wait_for_timeout(3000)

        self._started = True
        self._logged_in = await self._check_login_internal()
        self._sign_available = await self._check_sign_available()

        if self._logged_in:
            logger.info("XHS browser is already logged in")
            await self._save_state()
        else:
            logger.info("XHS browser is not logged in, login required")

    def start(self) -> None:
        with self._lock:
            self._submit(self._start_browser(), timeout=120)

    async def _check_sign_available(self) -> bool:
        if not self._page or self._page.is_closed():
            return False
        try:
            result = await self._page.evaluate("typeof window._webmsxyw === 'function'")
            return bool(result)
        except Exception:
            return False

    async def _check_login_internal(self) -> bool:
        if not self._context:
            return False
        try:
            cookies = await self._context.cookies()
            has_web_session = any(c["name"] == "web_session" and c["value"] for c in cookies)
            if has_web_session:
                return True
            has_a1 = any(c["name"] == "a1" and c["value"] for c in cookies)
            current_url = self._page.url if self._page else ""
            on_xhs = "xiaohongshu.com" in current_url
            return has_a1 and on_xhs
        except Exception:
            return False

    async def _ensure_on_xhs(self) -> None:
        if not self._page or self._page.is_closed():
            await self._start_browser()
            return

        current_url = self._page.url
        if "xiaohongshu.com" not in current_url:
            await self._page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
            await self._page.wait_for_timeout(2000)

        if not self._sign_available:
            self._sign_available = await self._check_sign_available()
            if not self._sign_available:
                await self._page.reload(wait_until="domcontentloaded")
                await self._page.wait_for_timeout(3000)
                self._sign_available = await self._check_sign_available()

    async def _sign_request(self, url: str, data: dict | None = None) -> dict[str, str]:
        if not self._started:
            await self._start_browser()

        if not self._logged_in:
            raise CollectionAuthError("XHS browser is not logged in. Please login first via /api/xhs-auth/start-login")

        await self._ensure_on_xhs()

        if not self._sign_available:
            raise CollectionRequestError("XHS signing function is not available in browser")

        sign_data = json.dumps(data, separators=(",", ":")) if data else ""

        try:
            result = await self._page.evaluate(
                "([url, data]) => { try { return window._webmsxyw(url, data); } catch(e) { return null; } }",
                [url, sign_data],
            )
        except Exception as error:
            raise CollectionRequestError(f"Failed to execute signing function: {error}") from error

        if not result or not isinstance(result, dict):
            raise CollectionRequestError("XHS signing function returned invalid result")

        headers: dict[str, str] = {}
        x_s = result.get("X-s") or result.get("x-s") or result.get("X-S") or ""
        x_t = result.get("X-t") or result.get("x-t") or result.get("X-T") or ""

        if x_s:
            headers["x-s"] = str(x_s)
        if x_t:
            headers["x-t"] = str(x_t)

        if not headers.get("x-s"):
            raise CollectionRequestError("XHS signing function did not return x-s header")

        return headers

    def sign(self, url: str, data: dict | None = None) -> dict[str, str]:
        with self._lock:
            return self._submit(self._sign_request(url, data), timeout=30)

    async def _get_qrcode(self) -> dict[str, Any]:
        if not self._started:
            await self._start_browser()

        await self._page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
        await self._page.wait_for_timeout(2000)

        login_btn_selectors = [
            "div.login-btn",
            "button:has-text('登录')",
            "a:has-text('登录')",
            ".sidebar-login-btn",
        ]

        clicked = False
        for selector in login_btn_selectors:
            try:
                locator = self._page.locator(selector)
                if await locator.count() > 0:
                    await locator.first.click()
                    clicked = True
                    break
            except Exception:
                continue

        if clicked:
            await self._page.wait_for_timeout(3000)

        qr_selectors = [
            ".qrcode-img img",
            ".login-qrcode img",
            "img[src*='qrcode']",
            "canvas",
        ]

        for selector in qr_selectors:
            try:
                locator = self._page.locator(selector)
                if await locator.count() > 0:
                    element = locator.first
                    if selector == "canvas":
                        qr_base64 = await element.screenshot(type="png")
                        return {
                            "qr_code": f"data:image/png;base64,{base64.b64encode(qr_base64).decode()}",
                            "type": "canvas",
                        }
                    src = await element.get_attribute("src")
                    if src:
                        if src.startswith("data:"):
                            return {"qr_code": src, "type": "data_uri"}
                        if src.startswith("http"):
                            return {"qr_code": src, "type": "url"}
            except Exception:
                continue

        try:
            qr_container = self._page.locator(".qrcode-container, .login-container, .login-modal")
            if await qr_container.count() > 0:
                screenshot = await qr_container.first.screenshot(type="png")
                return {
                    "qr_code": f"data:image/png;base64,{base64.b64encode(screenshot).decode()}",
                    "type": "screenshot",
                }
        except Exception:
            pass

        try:
            screenshot = await self._page.screenshot(type="png")
            return {
                "qr_code": f"data:image/png;base64,{base64.b64encode(screenshot).decode()}",
                "type": "full_page",
            }
        except Exception as error:
            raise CollectionRequestError(f"Failed to capture QR code: {error}") from error

    def get_qrcode(self) -> dict[str, Any]:
        with self._lock:
            return self._submit(self._get_qrcode(), timeout=30)

    async def _check_login_status(self) -> dict[str, Any]:
        if not self._started:
            return {"logged_in": False, "message": "Browser not started"}

        self._logged_in = await self._check_login_internal()

        if self._logged_in:
            self._sign_available = await self._check_sign_available()
            await self._save_state()
            return {"logged_in": True, "message": "Login successful, state saved"}
        return {"logged_in": False, "message": "Not logged in yet, please scan QR code"}

    def check_login_status(self) -> dict[str, Any]:
        with self._lock:
            return self._submit(self._check_login_status(), timeout=15)

    async def _save_state(self) -> None:
        if not self._context:
            return
        os.makedirs(self.state_dir, exist_ok=True)
        state_file = os.path.join(self.state_dir, "xhs_state.json")
        await self._context.storage_state(path=state_file)
        logger.info("Browser state saved to %s", state_file)

    def save_state(self) -> None:
        with self._lock:
            self._submit(self._save_state(), timeout=15)

    async def _get_cookies_string(self) -> str:
        if not self._context:
            return ""
        cookies = await self._context.cookies()
        return "; ".join(f'{c["name"]}={c["value"]}' for c in cookies)

    def get_cookies_string(self) -> str:
        with self._lock:
            return self._submit(self._get_cookies_string(), timeout=10)

    async def _get_a1_cookie(self) -> str:
        if not self._context:
            return ""
        cookies = await self._context.cookies()
        for c in cookies:
            if c["name"] == "a1":
                return c["value"]
        return ""

    def get_a1_cookie(self) -> str:
        with self._lock:
            return self._submit(self._get_a1_cookie(), timeout=10)

    async def _close_internal(self) -> None:
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._started = False
        self._logged_in = False
        self._sign_available = False

    def close(self) -> None:
        try:
            with self._lock:
                self._submit(self._close_internal(), timeout=15)
        except Exception:
            pass
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop = None
        self._thread = None

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    @property
    def is_sign_available(self) -> bool:
        return self._sign_available

    def get_status(self) -> dict[str, Any]:
        return {
            "started": self._started,
            "logged_in": self._logged_in,
            "sign_available": self._sign_available,
            "headless": self.headless,
            "state_dir": self.state_dir,
        }
