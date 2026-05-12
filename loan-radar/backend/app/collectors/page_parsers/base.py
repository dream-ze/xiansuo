from abc import ABC, abstractmethod
from typing import Any

from app.collectors.base import CollectorResult


class BasePageParser(ABC):
    @abstractmethod
    async def parse(
        self,
        page: Any,
        source_url: str,
        platform: str,
        browser_channel: str,
    ) -> CollectorResult:
        raise NotImplementedError

