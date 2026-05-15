from types import SimpleNamespace

import pytest

from app.collectors.factory import CollectorFactory
from app.collectors.media_crawler.collector import MediaCrawlerCollector
from app.collectors.config import CollectorConfig


def test_default_uses_media_crawler_collector():
    source = SimpleNamespace(
        source_type="keyword",
        platform="xhs",
        value="征信花了",
        config={},
    )

    collector = CollectorFactory.create(source)

    assert isinstance(collector, MediaCrawlerCollector)


def test_playwright_is_rejected():
    source = SimpleNamespace(
        source_type="manual_post",
        platform="xhs",
        value="https://example.com/post/1",
        config={"collector_type": "playwright"},
    )

    with pytest.raises(ValueError) as exc_info:
        CollectorFactory.create(source)

    assert "Unsupported collector_type: playwright" in str(exc_info.value)


def test_xhs_collector_type_no_longer_supported():
    source = SimpleNamespace(
        source_type="keyword",
        platform="xhs",
        value="征信花了",
        config={"collector_type": "xhs"},
    )

    with pytest.raises(ValueError) as exc_info:
        CollectorFactory.create(source)

    assert "Unsupported collector_type: xhs" in str(exc_info.value)


def test_media_crawler_config_validates_login_type():
    config = CollectorConfig.parse(
        {
            "collector_type": "media_crawler",
            "login_type": "cookie",
            "enable_comments": True,
        }
    )

    is_valid, message = config.validate_for_collector_type()

    assert is_valid is True
    assert message == ""


def test_supported_collectors_has_no_xhs():
    supported = CollectorFactory.get_supported_collectors()
    assert list(supported.keys()) == ["media_crawler"]
    assert "xhs" not in supported
    assert "media_crawler" in supported
