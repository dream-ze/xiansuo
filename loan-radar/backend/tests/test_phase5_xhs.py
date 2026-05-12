"""Phase 5 - XhsCollector 单元测试"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.config import CollectorConfig
from app.collectors.factory import CollectorFactory
from app.collectors.page_parsers.xhs import XhsPageParser
from app.collectors.xhs_collector import XhsCollector


class TestXhsCollectorBasic:
    """XhsCollector 基础测试"""

    def test_create_collector(self):
        """测试：创建 XhsCollector"""
        collector = XhsCollector()
        assert collector is not None

    def test_config_validation_missing_cookies(self):
        """测试：缺少 cookies 时配置验证失败"""
        collector = XhsCollector()
        source = SimpleNamespace(
            platform="xhs",
            value="https://www.xiaohongshu.com/explore",
            config={
                "collector_type": "xhs",
                "cookies": None,  # 缺少 cookies
            },
        )
        with pytest.raises(ValueError, match="xhs requires cookies"):
            collector.collect(source)

    def test_config_validation_missing_entry_url(self):
        """测试：缺少 entry_url"""
        collector = XhsCollector()
        source = SimpleNamespace(
            platform="xhs",
            value="",  # 空 URL
            config={
                "collector_type": "xhs",
                "cookies": "test_cookie=value",
            },
        )
        with pytest.raises(ValueError, match="entry URL"):
            collector.collect(source)

    def test_config_validation_invalid_url_scheme(self):
        """测试：无效 URL scheme"""
        collector = XhsCollector()
        source = SimpleNamespace(
            platform="xhs",
            value="ftp://invalid.url",  # 无效 scheme
            config={
                "collector_type": "xhs",
                "cookies": "test_cookie=value",
            },
        )
        with pytest.raises(ValueError, match="http/https URL"):
            collector.collect(source)

    def test_config_validation_valid(self):
        """测试：有效的 XHS 配置"""
        config = {
            "collector_type": "xhs",
            "entry_url": "https://www.xiaohongshu.com/explore",
            "cookies": "test_cookie=value",
            "max_posts": 20,
            "max_comments_per_post": 50,
        }
        config_obj = CollectorConfig.parse(config)
        assert config_obj.collector_type == "xhs"
        assert config_obj.cookies == "test_cookie=value"
        is_valid, msg = config_obj.validate_for_collector_type()
        assert is_valid


class TestXhsPageParser:
    """XhsPageParser 测试"""

    def test_parser_initialization(self):
        """测试：页面解析器初始化"""
        parser = XhsPageParser()
        assert parser is not None
        assert hasattr(parser, "selectors")
        assert parser.platform == "xhs"

    def test_parser_with_custom_max_comments(self):
        """测试：自定义最大评论数"""
        parser = XhsPageParser(max_comments_per_post=100)
        assert parser.max_comments_per_post == 100


class TestXhsCollectorFactory:
    """XhsCollector Factory 集成测试"""

    def test_factory_creates_xhs_collector(self):
        """测试：Factory 能创建 XhsCollector"""
        source = SimpleNamespace(
            platform="xhs",
            value="https://www.xiaohongshu.com/explore",
            config={
                "collector_type": "xhs",
                "cookies": "test_cookie=value",
                "entry_url": "https://www.xiaohongshu.com/explore",
            },
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, XhsCollector)

    def test_xhs_in_supported_collectors(self):
        """测试：xhs 在支持的采集器列表中"""
        capabilities = CollectorFactory.get_supported_collectors()
        assert "xhs" in capabilities
        assert capabilities["xhs"]["status"] == "ready"

    def test_xhs_capabilities(self):
        """测试：xhs 能力详情"""
        capabilities = CollectorFactory.get_supported_collectors()
        xhs_cap = capabilities["xhs"]
        assert "config" in xhs_cap
        assert xhs_cap["config"]["collector_type"] == "xhs"
        assert xhs_cap["config"]["cookies"] == "required"


class TestXhsCollectorConfig:
    """XhsCollector 配置测试"""

    def test_multiple_selectors(self):
        """测试：多选择器支持"""
        parser = XhsPageParser(
            selectors={
                "note_container": ".note-item, article",
                "title": "h2, .note-title",
                "content": "p, .note-content",
            }
        )
        assert parser.selectors["note_container"] == ".note-item, article"

    def test_default_selector_handling(self):
        """测试：默认选择器处理"""
        parser = XhsPageParser()
        assert "note_container" in parser.selectors
        assert "title" in parser.selectors
        assert "content" in parser.selectors
        assert "author" in parser.selectors
        assert "comment_item" in parser.selectors

    def test_max_posts_and_comments_config(self):
        """测试：max_posts 和 max_comments 配置"""
        parser = XhsPageParser(
            max_posts=50,
            max_comments_per_post=100,
        )
        assert parser.max_posts == 50
        assert parser.max_comments_per_post == 100


class TestXhsCollectorError:
    """XhsCollector 错误处理测试"""

    def test_missing_entry_url(self):
        """测试：缺少 entry_url"""
        collector = XhsCollector()
        source = SimpleNamespace(
            platform="xhs",
            value=None,
            config={
                "collector_type": "xhs",
                "cookies": "test_cookie=value",
            },
        )
        with pytest.raises(ValueError, match="entry URL|required"):
            collector.collect(source)

    def test_invalid_url_scheme(self):
        """测试：无效 URL scheme"""
        collector = XhsCollector()
        source = SimpleNamespace(
            platform="xhs",
            value="javascript:void(0)",
            config={
                "collector_type": "xhs",
                "cookies": "test_cookie=value",
            },
        )
        with pytest.raises(ValueError, match="http/https"):
            collector.collect(source)

    def test_config_validation_missing_cookies(self):
        """测试：缺少 cookies 验证"""
        config = {
            "collector_type": "xhs",
            "cookies": None,
        }
        config_obj = CollectorConfig.parse(config)
        is_valid, msg = config_obj.validate_for_collector_type()
        assert not is_valid
        assert "cookies" in msg


class TestXhsPageParserDefaults:
    """XhsPageParser 默认值测试"""

    def test_default_selectors_exist(self):
        """测试：默认选择器存在"""
        assert hasattr(XhsPageParser, "DEFAULT_SELECTORS")
        selectors = XhsPageParser.DEFAULT_SELECTORS
        assert isinstance(selectors, dict)
        assert len(selectors) > 0

    def test_custom_selectors_override_defaults(self):
        """测试：自定义选择器覆盖默认值"""
        custom = {"note_container": ".my-note"}
        parser = XhsPageParser(selectors=custom)
        assert parser.selectors["note_container"] == ".my-note"
        # 其他选择器仍然是默认值
        assert "title" in parser.selectors


class TestXhsCollectorCookieHandling:
    """XhsCollector Cookie 处理测试"""

    def test_cookies_string_format(self):
        """测试：Cookie 字符串格式支持"""
        config = {
            "collector_type": "xhs",
            "cookies": "sessionid=abc123; userid=user456; path=/; secure",
            "entry_url": "https://www.xiaohongshu.com/explore",
        }
        config_obj = CollectorConfig.parse(config)
        assert config_obj.cookies is not None
        assert "sessionid=abc123" in config_obj.cookies

    def test_cookies_json_format(self):
        """测试：Cookie JSON 格式支持"""
        import json
        
        cookies_list = [
            {"name": "sessionid", "value": "abc123"},
            {"name": "userid", "value": "user456"},
        ]
        cookies_json = json.dumps(cookies_list)
        
        config = {
            "collector_type": "xhs",
            "cookies": cookies_json,
            "entry_url": "https://www.xiaohongshu.com/explore",
        }
        config_obj = CollectorConfig.parse(config)
        assert config_obj.cookies is not None


class TestXhsCollectorIntegration:
    """XhsCollector 集成测试"""

    def test_xhs_vs_generic_web_collector_type(self):
        """测试：xhs 和 generic_web 是不同的采集器"""
        capabilities = CollectorFactory.get_supported_collectors()
        assert capabilities["xhs"]["status"] == "ready"
        assert capabilities["generic_web"]["status"] == "ready"
        assert capabilities["xhs"]["config"]["cookies"] == "required"

    def test_factory_rejects_unknown_collector_type(self):
        """测试：Factory 拒绝未知采集器类型"""
        source = SimpleNamespace(
            platform="unknown",
            config={"collector_type": "unknown_type"},
        )
        with pytest.raises(ValueError, match="Unsupported"):
            CollectorFactory.create(source)
