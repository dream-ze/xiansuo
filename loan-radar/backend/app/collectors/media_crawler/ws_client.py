"""WebSocket client for MediaCrawler API - 实时接收采集进度，替代 HTTP 轮询。

使用方式：
  from app.collectors.media_crawler.ws_client import MediaCrawlerWSClient

  client = MediaCrawlerWSClient()
  await client.connect()
  # client.wait_for_completion() 阻塞等待采集完成
  await client.disconnect()
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable

import httpx

from app.collectors.base import CollectionRequestError


class MediaCrawlerWSClient:
    """WebSocket client that listens to MediaCrawler log stream.

    MediaCrawler provides /api/ws/logs for real-time log streaming.
    This client connects to it and detects crawl completion events.
    """

    DEFAULT_WS_URL = "ws://127.0.0.1:8080/api/ws/logs"
    DEFAULT_API_URL = "http://127.0.0.1:8080"

    COMPLETION_PATTERNS = (
        "Crawler completed successfully",
        "Crawler process terminated",
        "采集完成",
        "数据保存完成",
    )

    ERROR_PATTERNS = (
        "Crawler exited with code",
        "Failed to start crawler",
        "Error stopping crawler",
        "采集失败",
    )

    def __init__(
        self,
        api_base_url: str | None = None,
        on_log: Callable[[dict], None] | None = None,
    ):
        self.api_base_url = (
            api_base_url
            or os.getenv("MEDIA_CRAWLER_API_URL", "")
            or self.DEFAULT_API_URL
        ).rstrip("/")
        self.ws_url = self.api_base_url.replace("http", "ws") + "/api/ws/logs"
        self.on_log = on_log
        self._ws = None
        self._done = asyncio.Event()
        self._error_message: str | None = None
        self._listen_task: asyncio.Task | None = None

    async def connect(self) -> None:
        try:
            import websockets
        except ImportError:
            raise CollectionRequestError(
                "websockets package not installed. "
                "Install it with: pip install websockets"
            )

        try:
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
            )
            self._done.clear()
            self._error_message = None
            self._listen_task = asyncio.create_task(self._listen())
        except Exception as exc:
            raise CollectionRequestError(
                f"无法连接 MediaCrawler WebSocket ({self.ws_url}): {exc}"
            ) from exc

    async def disconnect(self) -> None:
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def wait_for_completion(self, timeout: float = 600) -> dict[str, Any]:
        try:
            await asyncio.wait_for(self._done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise CollectionRequestError(
                f"等待 MediaCrawler 采集完成超时 ({timeout}s)"
            )

        if self._error_message:
            raise CollectionRequestError(f"MediaCrawler 采集失败: {self._error_message}")

        return self._get_final_status()

    def _get_final_status(self) -> dict[str, Any]:
        try:
            resp = httpx.get(
                f"{self.api_base_url}/api/crawler/status",
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}

    async def _listen(self) -> None:
        if not self._ws:
            return

        try:
            async for raw_message in self._ws:
                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode("utf-8")

                if raw_message == "ping":
                    try:
                        await self._ws.send("pong")
                    except Exception:
                        pass
                    continue

                try:
                    log_entry = json.loads(raw_message)
                except json.JSONDecodeError:
                    continue

                if self.on_log:
                    try:
                        self.on_log(log_entry)
                    except Exception:
                        pass

                message = str(log_entry.get("message", ""))
                level = str(log_entry.get("level", ""))

                for pattern in self.COMPLETION_PATTERNS:
                    if pattern.lower() in message.lower():
                        self._done.set()
                        return

                for pattern in self.ERROR_PATTERNS:
                    if pattern.lower() in message.lower():
                        self._error_message = message
                        self._done.set()
                        return

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._error_message = str(exc)
            self._done.set()
