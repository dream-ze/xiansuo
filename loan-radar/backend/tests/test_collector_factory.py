import os
from types import SimpleNamespace
from unittest.mock import patch

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
    assert "xhs" not in supported
    assert "media_crawler" in supported


def test_mock_collector_rejected_when_disabled():
    source = SimpleNamespace(
        source_type="keyword",
        platform="xhs",
        value="征信花了",
        config={"collector_type": "mock"},
    )

    with patch.dict(os.environ, {"ENABLE_MOCK_COLLECTOR": "false"}):
        with pytest.raises(ValueError) as exc_info:
            CollectorFactory.create(source)

        assert "mock collector is disabled" in str(exc_info.value)


def test_mock_collector_created_when_enabled():
    from app.collectors.mock_collector import MockCollector

    source = SimpleNamespace(
        source_type="keyword",
        platform="xhs",
        value="征信花了",
        config={"collector_type": "mock"},
    )

    with patch.dict(os.environ, {"ENABLE_MOCK_COLLECTOR": "true"}):
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MockCollector)


def test_mock_collector_config_validation_rejects_when_disabled():
    config = CollectorConfig.parse({"collector_type": "mock"})

    with patch.dict(os.environ, {"ENABLE_MOCK_COLLECTOR": "false"}):
        is_valid, msg = config.validate_collector_type()
        assert is_valid is False
        assert "mock collector is disabled" in msg


def test_mock_collector_config_validation_passes_when_enabled():
    config = CollectorConfig.parse({"collector_type": "mock"})

    with patch.dict(os.environ, {"ENABLE_MOCK_COLLECTOR": "true"}):
        is_valid, msg = config.validate_collector_type()
        assert is_valid is True
        assert msg == ""


def test_supported_collectors_includes_mock_when_enabled():
    with patch.dict(os.environ, {"ENABLE_MOCK_COLLECTOR": "true"}):
        supported = CollectorFactory.get_supported_collectors()
        assert "mock" in supported
        assert supported["mock"]["mode"] == "demo"
        assert "keyword" in supported["mock"]["supports"]


def test_supported_collectors_excludes_mock_when_disabled():
    with patch.dict(os.environ, {"ENABLE_MOCK_COLLECTOR": "false"}):
        supported = CollectorFactory.get_supported_collectors()
        assert "mock" not in supported


def test_mock_collector_generates_demo_data():
    from app.collectors.mock_collector import MockCollector

    source = SimpleNamespace(
        source_type="keyword",
        platform="xhs",
        value="征信花了",
        config={"collector_type": "mock"},
    )

    collector = MockCollector()
    result = collector.collect(source)

    assert len(result.posts) > 0
    assert len(result.comments) > 0

    for post in result.posts:
        assert post.raw_data.get("demo") is True
        assert post.post_id.startswith("demo-")

    for comment in result.comments:
        assert comment.raw_data.get("demo") is True
        assert comment.comment_id.startswith("demo-")

    assert result.metadata.get("demo") is True


def test_mock_collector_hot_post_rule():
    from app.collectors.mock_collector import MockCollector

    source = SimpleNamespace(
        source_type="hot_post_rule",
        platform="xhs",
        value="有逾期怎么处理",
        config={"collector_type": "mock"},
    )

    collector = MockCollector()
    result = collector.collect(source)

    assert len(result.posts) == 5
    for post in result.posts:
        assert post.is_hot is True
