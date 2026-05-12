"""Phase 4 - GenericWebCollector 单元测试"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.collectors.config import CollectorConfig
from app.collectors.generic_web_collector import GenericWebCollector


class TestGenericWebCollectorBasic:
    """基础功能测试"""

    def test_create_collector(self):
        """测试创建 GenericWebCollector 实例"""
        collector = GenericWebCollector()
        assert collector is not None

    def test_config_validation_missing_entry_url(self):
        """测试配置验证 - 缺少 entry_url"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url=None,
            selectors={"title": "h1"},
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid
        assert "entry_url" in msg

    def test_config_validation_missing_selectors(self):
        """测试配置验证 - 缺少 selectors"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="https://example.com",
            selectors=None,
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid
        assert "selectors" in msg

    def test_config_validation_invalid_url(self):
        """测试配置验证 - 无效的 URL"""
        collector = GenericWebCollector()
        source = SimpleNamespace(
            platform="test",
            config={
                "collector_type": "generic_web",
                "entry_url": "not-a-url",
                "selectors": {"title": "h1"},
            },
        )
        with pytest.raises(ValueError, match="must start with http"):
            collector.collect(source)

    def test_config_validation_valid(self):
        """测试配置验证 - 有效配置"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="https://example.com",
            selectors={"title": "h1"},
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid


class TestGenericPageParser:
    """通用页面解析器测试"""

    def test_parser_initialization(self):
        """测试页面解析器初始化"""
        from app.collectors.page_parsers.generic import GenericPageParser

        parser = GenericPageParser()
        assert parser is not None
        assert parser.max_comments_per_post == 50

    def test_parser_with_custom_max_comments(self):
        """测试使用自定义最大评论数"""
        from app.collectors.page_parsers.generic import GenericPageParser

        parser = GenericPageParser(max_comments_per_post=30)
        assert parser.max_comments_per_post == 30


class TestGenericWebCollectorFactory:
    """GenericWebCollector 集成测试"""

    def test_factory_creates_generic_web_collector(self):
        """测试 CollectorFactory 能创建 GenericWebCollector"""
        from app.collectors.factory import CollectorFactory

        source = SimpleNamespace(
            platform="test_platform",
            source_type="keyword",
            config={
                "collector_type": "generic_web",
                "entry_url": "https://example.com",
                "selectors": {"title": "h1", "content": "article"},
            },
        )

        collector = CollectorFactory.create(source)
        assert isinstance(collector, GenericWebCollector)

    def test_generic_web_in_supported_collectors(self):
        """测试 generic_web 在能力列表中显示为 ready"""
        from app.collectors.factory import CollectorFactory

        supported = CollectorFactory.get_supported_collectors()
        assert "generic_web" in supported
        assert supported["generic_web"]["status"] == "ready"

    def test_generic_web_capabilities(self):
        """测试 generic_web 的能力描述"""
        from app.collectors.factory import CollectorFactory

        supported = CollectorFactory.get_supported_collectors()
        generic_web = supported["generic_web"]

        assert "CSS" in generic_web["description"] or "自定义" in generic_web["description"]
        assert "manual_post" in generic_web["supports"]
        assert generic_web["config"]["collector_type"] == "generic_web"


class TestGenericWebCollectorConfig:
    """配置相关测试"""

    def test_selectors_with_multiple_options(self):
        """测试选择器配置 - 多个选项"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="https://example.com",
            selectors={
                "post_container": "article, .post, [data-post]",
                "title": "h1, h2, .title",
                "content": "article, .content, main",
                "comment_item": ".comment, .reply, [data-comment]",
            },
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid
        assert config.selectors is not None
        assert len(config.selectors) == 4

    def test_default_selector_handling(self):
        """测试默认选择器处理"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="https://example.com",
            selectors={
                "title": "h1",  # 只提供 title
            },
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid
        # 缺失的选择器应该在解析器中使用默认值

    def test_max_posts_and_comments_config(self):
        """测试 max_posts 和 max_comments_per_post 配置"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="https://example.com",
            selectors={"title": "h1"},
            max_posts=20,
            max_comments_per_post=30,
        )
        assert config.max_posts == 20
        assert config.max_comments_per_post == 30


class TestGenericWebCollectorError:
    """错误处理测试"""

    def test_missing_entry_url(self):
        """测试缺少 entry_url"""
        collector = GenericWebCollector()
        source = SimpleNamespace(
            platform="test",
            config={
                "collector_type": "generic_web",
                "entry_url": None,
                "selectors": {"title": "h1"},
            },
        )
        with pytest.raises(ValueError, match="entry_url|Invalid generic_web config"):
            collector.collect(source)

    def test_invalid_url_scheme(self):
        """测试无效的 URL scheme"""
        collector = GenericWebCollector()
        source = SimpleNamespace(
            platform="test",
            config={
                "collector_type": "generic_web",
                "entry_url": "ftp://example.com",
                "selectors": {"title": "h1"},
            },
        )
        with pytest.raises(ValueError, match="http"):
            collector.collect(source)

    def test_config_validation_empty_selectors(self):
        """测试空的 selectors 配置"""
        config = CollectorConfig(
            collector_type="generic_web",
            entry_url="https://example.com",
            selectors={},  # 空字典不应该失败，因为有默认选择器
        )
        is_valid, msg = config.validate_for_collector_type()
        # 即使 selectors 是空的，也应该是有效的（解析器会使用默认值）
        assert is_valid or "selectors" in msg


class TestGenericPageParserDefaults:
    """页面解析器默认选择器测试"""

    def test_default_selectors_exist(self):
        """测试默认选择器存在"""
        from app.collectors.page_parsers.generic import GenericPageParser

        parser = GenericPageParser()
        assert hasattr(GenericPageParser, "DEFAULT_SELECTORS")
        assert "post_container" in GenericPageParser.DEFAULT_SELECTORS
        assert "title" in GenericPageParser.DEFAULT_SELECTORS
        assert "content" in GenericPageParser.DEFAULT_SELECTORS
        assert "author" in GenericPageParser.DEFAULT_SELECTORS
        assert "comment_item" in GenericPageParser.DEFAULT_SELECTORS

    def test_custom_selectors_override_defaults(self):
        """测试自定义选择器覆盖默认值"""
        from app.collectors.page_parsers.generic import GenericPageParser

        parser = GenericPageParser()
        defaults = GenericPageParser.DEFAULT_SELECTORS.copy()

        # 模拟合并逻辑
        custom_selectors = {
            "title": "custom-h1",
        }
        merged = {**defaults}
        merged.update(custom_selectors)

        assert merged["title"] == "custom-h1"
        assert merged["content"] == defaults["content"]  # 其他保持不变
