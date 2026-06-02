import pytest
from types import SimpleNamespace

from app.collectors.base import CollectorResult, CollectedPost, CollectedComment
from app.collectors.config import CollectorConfig
from app.collectors.factory import CollectorFactory
from app.collectors.media_crawler.embedded_collector import EmbeddedMediaCrawlerCollector
from app.collectors.media_crawler.collector import MediaCrawlerCollector


class TestCollectorResult:
    def test_collector_result_with_metadata(self):
        result = CollectorResult(
            posts=[],
            comments=[],
            metadata={"source": "media_crawler", "notes_searched": 5},
        )
        assert result.metadata == {"source": "media_crawler", "notes_searched": 5}

    def test_collector_result_metadata_optional(self):
        result = CollectorResult(posts=[], comments=[])
        assert result.metadata is None

    def test_collector_result_serialization(self):
        result = CollectorResult(
            posts=[],
            comments=[],
            metadata={"test": "value"},
        )
        data = result.dict()
        assert data["metadata"] == {"test": "value"}


class TestCollectorConfig:
    def test_collector_config_defaults(self):
        config = CollectorConfig()
        assert config.collector_type == "media_crawler"
        assert config.mode == "test"
        assert config.max_posts == 10
        assert config.max_comments_per_post == 50

    def test_collector_config_parse_dict(self):
        data = {
            "collector_type": "media_crawler",
            "max_posts": 20,
        }
        config = CollectorConfig.parse(data)
        assert config.collector_type == "media_crawler"
        assert config.max_posts == 20

    def test_collector_config_parse_object(self):
        source = SimpleNamespace(
            collector_type="media_crawler",
            cookies="test_cookie",
        )
        config = CollectorConfig.parse(source)
        assert config.collector_type == "media_crawler"
        assert config.cookies == "test_cookie"

    def test_collector_config_validate_collector_type(self):
        config = CollectorConfig(collector_type="unknown")
        is_valid, msg = config.validate_collector_type()
        assert not is_valid
        assert "Unsupported" in msg

    def test_collector_config_validate_supported_types(self):
        config = CollectorConfig(collector_type="media_crawler")
        is_valid, msg = config.validate_collector_type()
        assert is_valid, f"media_crawler validation failed: {msg}"

    def test_collector_config_xhs_not_supported(self):
        config = CollectorConfig(collector_type="xhs")
        is_valid, msg = config.validate_collector_type()
        assert not is_valid
        assert "Unsupported" in msg

    def test_collector_config_validate_media_crawler(self):
        config = CollectorConfig(collector_type="media_crawler")
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid

        config = CollectorConfig(
            collector_type="media_crawler",
            login_type="qrcode",
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid

        config = CollectorConfig(
            collector_type="media_crawler",
            login_type="cookie",
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid

        config = CollectorConfig(
            collector_type="media_crawler",
            login_type="invalid",
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid


class TestCollectorFactory:
    def test_factory_create_media_crawler(self, monkeypatch):
        monkeypatch.delenv("MEDIA_CRAWLER_HOME", raising=False)
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "media_crawler"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MediaCrawlerCollector)

    def test_factory_create_default_media_crawler(self, monkeypatch):
        monkeypatch.delenv("MEDIA_CRAWLER_HOME", raising=False)
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MediaCrawlerCollector)

    def test_factory_create_embedded_media_crawler_when_home_exists(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MEDIA_CRAWLER_HOME", str(tmp_path))
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "media_crawler"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, EmbeddedMediaCrawlerCollector)

    def test_factory_reject_unknown_collector_type(self):
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "unknown_collector"},
        )
        with pytest.raises(ValueError) as exc_info:
            CollectorFactory.create(source)
        assert "unsupported" in str(exc_info.value).lower()

    def test_factory_reject_xhs_collector_type(self):
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "xhs"},
        )
        with pytest.raises(ValueError) as exc_info:
            CollectorFactory.create(source)
        assert "Unsupported collector_type: xhs" in str(exc_info.value)

    def test_factory_douyin_via_media_crawler(self, monkeypatch):
        monkeypatch.delenv("MEDIA_CRAWLER_HOME", raising=False)
        source = SimpleNamespace(
            source_type="keyword",
            platform="douyin",
            config={"collector_type": "media_crawler"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MediaCrawlerCollector)

    def test_factory_zhihu_via_media_crawler(self, monkeypatch):
        monkeypatch.delenv("MEDIA_CRAWLER_HOME", raising=False)
        source = SimpleNamespace(
            source_type="keyword",
            platform="zhihu",
            config={"collector_type": "media_crawler"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MediaCrawlerCollector)

    def test_factory_get_supported_collectors(self):
        collectors = CollectorFactory.get_supported_collectors()
        assert "media_crawler" in collectors
        assert "xhs" not in collectors
        assert "mock" not in collectors
        assert "playwright" not in collectors
        assert collectors["media_crawler"]["status"] == "ready"
