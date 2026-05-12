from types import SimpleNamespace

import pytest

from app.collectors.factory import CollectorFactory
from app.collectors.mock_collector import MockCollector
from app.collectors.playwright_collector import PlaywrightCollector


def test_manual_post_playwright_uses_playwright_collector():
    source = SimpleNamespace(
        source_type="manual_post",
        platform="xhs",
        value="https://example.com/post/1",
        config={"collector_type": "playwright"},
    )

    collector = CollectorFactory.create(source)

    assert isinstance(collector, PlaywrightCollector)


def test_keyword_playwright_raises_error():
    """keyword + playwright 应抛出错误，而不是 fallback 到 mock"""
    source = SimpleNamespace(
        source_type="keyword",
        platform="xhs",
        value="征信花了",
        config={"collector_type": "playwright"},
    )

    with pytest.raises(ValueError) as exc_info:
        CollectorFactory.create(source)
    
    assert "manual_post" in str(exc_info.value)


