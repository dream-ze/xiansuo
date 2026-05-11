from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.mock_collector import MockCollector
from app.collectors.playwright_collector import PlaywrightCollector


class CollectorFactory:
    @staticmethod
    def create(source: Any) -> BaseCollector:
        config = getattr(source, "config", None) or {}
        collector_type = config.get("collector_type", "mock")
        source_type = getattr(source, "source_type", "")

        if collector_type == "playwright" and source_type == "manual_post":
            return PlaywrightCollector()

        return MockCollector()
