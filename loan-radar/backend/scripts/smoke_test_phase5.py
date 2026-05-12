#!/usr/bin/env python
"""Phase 5 - XhsCollector 烟雾测试"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace
from app.collectors.factory import CollectorFactory
from app.collectors.xhs_collector import XhsCollector
from app.collectors.page_parsers.xhs import XhsPageParser

def test_1_create_collector():
    """测试：创建 XhsCollector 采集器"""
    print("✓ Test 1: Create XhsCollector")
    collector = XhsCollector()
    assert collector is not None
    print("  PASS - XhsCollector 创建成功")

def test_2_factory_creation():
    """测试：通过 Factory 创建 XhsCollector"""
    print("\n✓ Test 2: Factory creates XhsCollector")
    source = SimpleNamespace(
        platform="xhs",
        value="https://www.xiaohongshu.com/explore",
        config={
            "collector_type": "xhs",
            "cookies": "test_sessionid=value123",
            "entry_url": "https://www.xiaohongshu.com/explore",
        },
    )
    collector = CollectorFactory.create(source)
    assert isinstance(collector, XhsCollector)
    print("  PASS - Factory 成功创建 XhsCollector")

def test_3_capability_listing():
    """测试：xhs 在支持的采集器列表中"""
    print("\n✓ Test 3: Capability listing")
    capabilities = CollectorFactory.get_supported_collectors()
    assert "xhs" in capabilities
    assert capabilities["xhs"]["status"] == "ready"
    print(f"  PASS - xhs 状态: {capabilities['xhs']['status']}")

def test_4_config_validation():
    """测试：XhsCollector 配置验证"""
    print("\n✓ Test 4: Config validation")
    from app.collectors.config import CollectorConfig
    
    config_dict = {
        "collector_type": "xhs",
        "cookies": "sessionid=abc123; userid=user456",
        "entry_url": "https://www.xiaohongshu.com/explore",
        "max_posts": 20,
        "max_comments_per_post": 100,
    }
    config = CollectorConfig.parse(config_dict)
    assert config.collector_type == "xhs"
    assert config.cookies is not None
    is_valid, msg = config.validate_for_collector_type()
    assert is_valid
    print("  PASS - 配置验证成功")

def test_5_parser_default_selectors():
    """测试：Parser 默认选择器"""
    print("\n✓ Test 5: Parser default selectors")
    parser = XhsPageParser()
    assert hasattr(parser, "selectors")
    assert "note_container" in parser.selectors
    assert "title" in parser.selectors
    assert "content" in parser.selectors
    assert "author" in parser.selectors
    print(f"  PASS - Parser 包含默认选择器: {list(parser.selectors.keys())}")

def test_6_custom_selectors():
    """测试：自定义选择器"""
    print("\n✓ Test 6: Custom selectors")
    custom_selectors = {
        "note_container": ".xhs-note",
        "title": ".xhs-title",
        "content": ".xhs-content",
        "author": ".xhs-author",
        "comment_item": ".xhs-comment",
    }
    parser = XhsPageParser(
        selectors=custom_selectors,
        max_posts=50,
        max_comments_per_post=100,
    )
    assert parser.selectors["note_container"] == ".xhs-note"
    assert parser.max_posts == 50
    assert parser.max_comments_per_post == 100
    print("  PASS - 自定义选择器设置成功")

def test_7_cookie_handling():
    """测试：Cookie 处理"""
    print("\n✓ Test 7: Cookie handling")
    cookies = "sessionid=abc123; userid=user456; path=/; secure"
    
    from app.collectors.config import CollectorConfig
    config = CollectorConfig.parse({
        "collector_type": "xhs",
        "cookies": cookies,
    })
    assert config.cookies is not None
    assert "sessionid" in config.cookies
    print("  PASS - Cookie 处理成功")

def test_8_xhs_vs_generic_web():
    """测试：xhs 和 generic_web 的区别"""
    print("\n✓ Test 8: XHS vs Generic Web distinction")
    capabilities = CollectorFactory.get_supported_collectors()
    
    xhs_config = capabilities["xhs"]["config"]
    generic_config = capabilities["generic_web"]["config"]
    
    # XHS 需要 cookies
    assert xhs_config.get("cookies") == "required"
    # Generic Web 需要 selectors 但不需要 cookies
    assert "selectors" in generic_config
    assert "cookies" not in generic_config or generic_config.get("cookies") != "required"
    
    print("  PASS - XHS 和 Generic Web 差异验证成功")

def main():
    """运行所有烟雾测试"""
    print("=" * 60)
    print("Phase 5 - XhsCollector 烟雾测试")
    print("=" * 60)
    
    try:
        test_1_create_collector()
        test_2_factory_creation()
        test_3_capability_listing()
        test_4_config_validation()
        test_5_parser_default_selectors()
        test_6_custom_selectors()
        test_7_cookie_handling()
        test_8_xhs_vs_generic_web()
        
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
