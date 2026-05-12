#!/usr/bin/env python
"""Phase 4 - GenericWebCollector 烟雾测试"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace
from app.collectors.factory import CollectorFactory
from app.collectors.generic_web_collector import GenericWebCollector
from app.collectors.page_parsers.generic import GenericPageParser

def test_1_create_collector():
    """测试：创建 GenericWebCollector 采集器"""
    print("✓ Test 1: Create GenericWebCollector")
    collector = GenericWebCollector()
    assert collector is not None
    print("  PASS - GenericWebCollector 创建成功")

def test_2_factory_creation():
    """测试：通过 Factory 创建 GenericWebCollector"""
    print("\n✓ Test 2: Factory creates GenericWebCollector")
    source = SimpleNamespace(
        platform="test",
        config={
            "collector_type": "generic_web",
            "entry_url": "https://example.com",
            "selectors": {"post_container": ".post"},
        },
    )
    collector = CollectorFactory.create(source)
    assert isinstance(collector, GenericWebCollector)
    print("  PASS - Factory 成功创建 GenericWebCollector")

def test_3_capability_listing():
    """测试：generic_web 在支持的采集器列表中"""
    print("\n✓ Test 3: Capability listing")
    capabilities = CollectorFactory.get_supported_collectors()
    assert "generic_web" in capabilities
    assert capabilities["generic_web"]["status"] == "ready"
    print(f"  PASS - generic_web 状态: {capabilities['generic_web']['status']}")

def test_4_config_validation():
    """测试：GenericWebCollector 配置验证"""
    print("\n✓ Test 4: Config validation")
    from app.collectors.config import CollectorConfig
    
    config_dict = {
        "collector_type": "generic_web",
        "entry_url": "https://example.com",
        "selectors": {"title": "h1", "content": "p"},
    }
    config = CollectorConfig.parse(config_dict)
    assert config.collector_type == "generic_web"
    assert config.entry_url == "https://example.com"
    assert config.selectors is not None
    print("  PASS - 配置验证成功")

def test_5_parser_default_selectors():
    """测试：Parser 默认选择器"""
    print("\n✓ Test 5: Parser default selectors")
    parser = GenericPageParser()
    assert hasattr(parser, 'selectors')
    assert 'post_container' in parser.selectors
    assert 'title' in parser.selectors
    assert 'content' in parser.selectors
    print(f"  PASS - Parser 包含默认选择器: {list(parser.selectors.keys())}")

def test_6_custom_selectors():
    """测试：自定义选择器"""
    print("\n✓ Test 6: Custom selectors")
    custom_selectors = {
        "post_container": ".my-post",
        "title": ".post-title",
        "content": ".post-content",
        "author": ".post-author",
        "comment_item": ".my-comment",
    }
    parser = GenericPageParser(selectors=custom_selectors, max_posts=10, max_comments=5)
    assert parser.selectors["post_container"] == ".my-post"
    assert parser.max_posts == 10
    assert parser.max_comments == 5
    print("  PASS - 自定义选择器设置成功")

def main():
    """运行所有烟雾测试"""
    print("=" * 60)
    print("Phase 4 - GenericWebCollector 烟雾测试")
    print("=" * 60)
    
    try:
        test_1_create_collector()
        test_2_factory_creation()
        test_3_capability_listing()
        test_4_config_validation()
        test_5_parser_default_selectors()
        test_6_custom_selectors()
        
        print("\n" + "=" * 60)
        print("✅ 所有烟雾测试通过！")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ 烟雾测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
