"""Phase 1: 采集器基础设施测试"""

import pytest
from types import SimpleNamespace

from app.collectors.base import CollectorResult, CollectedPost, CollectedComment
from app.collectors.config import CollectorConfig
from app.collectors.factory import CollectorFactory
from app.collectors.mock_collector import MockCollector
from app.collectors.playwright_collector import PlaywrightCollector


class TestCollectorResult:
    """测试 CollectorResult metadata 字段"""

    def test_collector_result_with_metadata(self):
        """CollectorResult 应支持 metadata 字段"""
        result = CollectorResult(
            posts=[],
            comments=[],
            metadata={"source": "mock", "notes_searched": 5},
        )
        assert result.metadata == {"source": "mock", "notes_searched": 5}

    def test_collector_result_metadata_optional(self):
        """metadata 应为可选字段"""
        result = CollectorResult(posts=[], comments=[])
        assert result.metadata is None

    def test_collector_result_serialization(self):
        """CollectorResult 应可序列化为 JSON"""
        result = CollectorResult(
            posts=[],
            comments=[],
            metadata={"test": "value"},
        )
        data = result.dict()
        assert data["metadata"] == {"test": "value"}


class TestCollectorConfig:
    """测试 CollectorConfig 配置解析"""

    def test_collector_config_defaults(self):
        """CollectorConfig 应有合理的默认值"""
        config = CollectorConfig()
        assert config.collector_type == "mock"
        assert config.mode == "test"
        assert config.max_posts == 10
        assert config.max_comments_per_post == 50

    def test_collector_config_parse_dict(self):
        """CollectorConfig 应能从字典解析"""
        data = {
            "collector_type": "playwright",
            "max_posts": 20,
        }
        config = CollectorConfig.parse(data)
        assert config.collector_type == "playwright"
        assert config.max_posts == 20

    def test_collector_config_parse_object(self):
        """CollectorConfig 应能从对象解析"""
        source = SimpleNamespace(
            collector_type="xhs",
            cookies="test_cookie",
        )
        config = CollectorConfig.parse(source)
        assert config.collector_type == "xhs"
        assert config.cookies == "test_cookie"

    def test_collector_config_validate_collector_type(self):
        """CollectorConfig 应能验证 collector_type"""
        config = CollectorConfig(collector_type="unknown")
        is_valid, msg = config.validate_collector_type()
        assert not is_valid
        assert "Unsupported" in msg

    def test_collector_config_validate_supported_types(self):
        """CollectorConfig 应支持所有已列举的类型"""
        for collector_type in ["mock", "playwright", "xhs", "douyin", "zhihu", "external_api", "generic_web"]:
            config = CollectorConfig(collector_type=collector_type)
            is_valid, msg = config.validate_collector_type()
            assert is_valid, f"{collector_type} validation failed: {msg}"

    def test_collector_config_validate_external_api(self):
        """CollectorConfig 应验证 external_api 配置"""
        # 缺少 external_api 配置
        config = CollectorConfig(collector_type="external_api")
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid

        # 缺少 endpoint
        config = CollectorConfig(
            collector_type="external_api",
            external_api={},
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid

        # 有效配置
        config = CollectorConfig(
            collector_type="external_api",
            external_api={"endpoint": "http://example.com/api"},
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid

    def test_collector_config_validate_generic_web(self):
        """CollectorConfig 应验证 generic_web 配置"""
        # 缺少 entry_url 和 selectors
        config = CollectorConfig(collector_type="generic_web")
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid

        # 有效配置
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="http://example.com",
            selectors={"title": "h1"},
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid

    def test_collector_config_validate_xhs(self):
        """CollectorConfig 应验证 xhs 配置"""
        # 缺少 cookies
        config = CollectorConfig(collector_type="xhs")
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid

        # 有效配置
        config = CollectorConfig(
            collector_type="xhs",
            cookies="test_cookie",
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid


class TestCollectorFactory:
    """测试 CollectorFactory 严格路由"""

    def test_factory_create_mock_collector(self):
        """Factory 应能创建 MockCollector"""
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "mock"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MockCollector)

    def test_factory_create_default_mock_collector(self):
        """Factory 默认应创建 MockCollector"""
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MockCollector)

    def test_factory_create_playwright_collector(self):
        """Factory 应能创建 PlaywrightCollector（manual_post）"""
        source = SimpleNamespace(
            source_type="manual_post",
            platform="xhs",
            config={"collector_type": "playwright"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, PlaywrightCollector)

    def test_factory_reject_keyword_with_playwright(self):
        """Factory 应拒绝 keyword + playwright 组合"""
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "playwright"},
        )
        with pytest.raises(ValueError) as exc_info:
            CollectorFactory.create(source)
        assert "manual_post" in str(exc_info.value)

    def test_factory_reject_unknown_collector_type(self):
        """Factory 应拒绝未知的 collector_type"""
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "unknown_collector"},
        )
        with pytest.raises(ValueError) as exc_info:
            CollectorFactory.create(source)
        assert "unknown" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()

    def test_factory_xhs_not_implemented(self):
        """Factory 应能创建 xhs 采集器（Phase 5 实现）"""
        from app.collectors.xhs_collector import XhsCollector
        
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={
                "collector_type": "xhs",
                "cookies": "test",
                "entry_url": "https://www.xiaohongshu.com/explore",
            },
        )
        # Phase 5 已实现，应该能创建采集器
        collector = CollectorFactory.create(source)
        assert isinstance(collector, XhsCollector)

    def test_factory_douyin_not_implemented(self):
        """Factory 应提示 douyin 未实现"""
        source = SimpleNamespace(
            source_type="keyword",
            platform="douyin",
            config={"collector_type": "douyin"},
        )
        with pytest.raises(NotImplementedError) as exc_info:
            CollectorFactory.create(source)
        assert "Phase 6" in str(exc_info.value)

    def test_factory_zhihu_not_implemented(self):
        """Factory 应提示 zhihu 未实现"""
        source = SimpleNamespace(
            source_type="keyword",
            platform="zhihu",
            config={"collector_type": "zhihu"},
        )
        with pytest.raises(NotImplementedError) as exc_info:
            CollectorFactory.create(source)
        assert "Phase 6" in str(exc_info.value)

    def test_factory_external_api_not_implemented(self):
        """Factory 应能创建 external_api 采集器（Phase 3 实现）"""
        from app.collectors.external_api_collector import ExternalApiCollector
        
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            config={"collector_type": "external_api", "external_api": {"endpoint": "http://example.com"}},
        )
        # Phase 3 已实现，应该能创建采集器
        collector = CollectorFactory.create(source)
        assert isinstance(collector, ExternalApiCollector)

    def test_factory_generic_web_not_implemented(self):
        """Factory 应能创建 generic_web 采集器（Phase 4 实现）"""
        from app.collectors.generic_web_collector import GenericWebCollector
        
        source = SimpleNamespace(
            source_type="manual_post",
            platform="other",
            config={"collector_type": "generic_web", "entry_url": "http://example.com", "selectors": {}},
        )
        # Phase 4 已实现，应该能创建采集器
        collector = CollectorFactory.create(source)
        assert isinstance(collector, GenericWebCollector)

    def test_factory_get_supported_collectors(self):
        """Factory 应能返回支持的采集器列表"""
        collectors = CollectorFactory.get_supported_collectors()
        assert "mock" in collectors
        assert "playwright" in collectors
        assert "xhs" in collectors
        assert collectors["mock"]["status"] == "ready"
        assert collectors["xhs"]["status"] == "ready"  # Phase 5 完成
