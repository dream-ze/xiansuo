#!/usr/bin/env python
"""Phase 3 - ExternalApiCollector 烟雾测试"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# 添加 backend 到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.collectors.external_api_collector import ExternalApiCollector
from app.collectors.factory import CollectorFactory
from app.collectors.base import CollectorResult


def test_1_create_collector():
    """TEST 1: 创建 ExternalApiCollector 实例"""
    print("\n" + "=" * 60)
    print("TEST 1: 创建 ExternalApiCollector 实例")
    print("=" * 60)
    try:
        collector = ExternalApiCollector()
        assert collector is not None
        print("✅ PASS - ExternalApiCollector 创建成功")
        return True
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        return False


def test_2_factory_creates_external_api():
    """TEST 2: CollectorFactory 能创建 ExternalApiCollector"""
    print("\n" + "=" * 60)
    print("TEST 2: CollectorFactory 创建 ExternalApiCollector")
    print("=" * 60)
    try:
        os.environ["TEST_API_KEY"] = "test_key_123"
        source = SimpleNamespace(
            platform="test_platform",
            source_type="keyword",
            config={
                "collector_type": "external_api",
                "external_api": {
                    "endpoint": "https://api.example.com/collect",
                    "api_key_env": "TEST_API_KEY",
                },
            },
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, ExternalApiCollector)
        print("✅ PASS - CollectorFactory 正确路由到 ExternalApiCollector")
        return True
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        return False


def test_3_external_api_in_capabilities():
    """TEST 3: external_api 在能力列表中状态为 ready"""
    print("\n" + "=" * 60)
    print("TEST 3: 能力列表中的 external_api 状态")
    print("=" * 60)
    try:
        capabilities = CollectorFactory.get_supported_collectors()
        assert "external_api" in capabilities
        assert capabilities["external_api"]["status"] == "ready"
        print(f"✅ PASS - external_api 状态: {capabilities['external_api']['status']}")
        print(f"   描述: {capabilities['external_api']['description']}")
        return True
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        return False


def test_4_api_call_with_mock():
    """TEST 4: Mock API 调用测试"""
    print("\n" + "=" * 60)
    print("TEST 4: Mock API 调用测试")
    print("=" * 60)
    try:
        with patch("app.collectors.external_api_collector.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "posts": [
                    {
                        "post_id": "post_123",
                        "title": "Test Post",
                        "content": "Test content",
                        "author_name": "Test Author",
                        "like_count": 100,
                        "comment_count": 10,
                    },
                ],
                "comments": [
                    {
                        "post_id": "post_123",
                        "comment_id": "cmt_456",
                        "content": "Great post!",
                        "user_name": "Test User",
                        "like_count": 5,
                    },
                ],
            }
            mock_post.return_value = mock_response

            os.environ["TEST_API_KEY"] = "test_key_123"
            source = SimpleNamespace(
                platform="test_platform",
                config={
                    "collector_type": "external_api",
                    "external_api": {
                        "endpoint": "https://api.example.com/collect",
                        "api_key_env": "TEST_API_KEY",
                    },
                    "max_posts": 10,
                    "max_comments_per_post": 50,
                    "timeout_seconds": 30,
                    "retry_times": 3,
                    "rate_limit_seconds": 1,
                },
            )

            collector = ExternalApiCollector()
            result = collector.collect(source)

            assert isinstance(result, CollectorResult)
            assert len(result.posts) == 1
            assert len(result.comments) == 1
            assert result.posts[0].post_id == "post_123"
            assert result.comments[0].comment_id == "cmt_456"
            print("✅ PASS - API 调用成功")
            print(f"   获取 posts: {len(result.posts)}")
            print(f"   获取 comments: {len(result.comments)}")
            print(f"   Metadata: {result.metadata}")
            return True
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_5_generate_missing_ids():
    """TEST 5: 生成缺失的 post_id 和 comment_id"""
    print("\n" + "=" * 60)
    print("TEST 5: 生成缺失的 ID")
    print("=" * 60)
    try:
        with patch("app.collectors.external_api_collector.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "posts": [
                    {
                        # 缺少 post_id
                        "title": "Post Without ID",
                        "content": "Content",
                    },
                ],
                "comments": [
                    {
                        "post_id": "post_123",
                        # 缺少 comment_id
                        "content": "Comment",
                    },
                ],
            }
            mock_post.return_value = mock_response

            os.environ["TEST_API_KEY"] = "test_key"
            source = SimpleNamespace(
                platform="test_platform",
                config={
                    "collector_type": "external_api",
                    "external_api": {
                        "endpoint": "https://api.example.com/collect",
                        "api_key_env": "TEST_API_KEY",
                    },
                    "max_posts": 10,
                    "max_comments_per_post": 50,
                    "timeout_seconds": 30,
                    "retry_times": 1,
                    "rate_limit_seconds": 0,
                },
            )

            collector = ExternalApiCollector()
            result = collector.collect(source)

            assert result.posts[0].post_id is not None
            assert len(result.posts[0].post_id) == 16  # SHA1 前 16 位
            assert result.comments[0].comment_id is not None
            assert len(result.comments[0].comment_id) == 16
            print("✅ PASS - 成功生成缺失的 ID")
            print(f"   生成的 post_id: {result.posts[0].post_id}")
            print(f"   生成的 comment_id: {result.comments[0].comment_id}")
            return True
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        return False


def test_6_config_validation():
    """TEST 6: 配置验证"""
    print("\n" + "=" * 60)
    print("TEST 6: 配置验证")
    print("=" * 60)
    try:
        from app.collectors.config import CollectorConfig

        # 测试缺少 endpoint
        config = CollectorConfig(
            collector_type="external_api",
            external_api={},  # 缺少 endpoint
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid
        print(f"✅ PASS - 缺少 endpoint 检测: {msg}")

        # 测试缺少 external_api
        config = CollectorConfig(
            collector_type="external_api",
            external_api=None,
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid
        print(f"✅ PASS - 缺少 external_api 检测: {msg}")

        # 测试有效配置
        config = CollectorConfig(
            collector_type="external_api",
            external_api={"endpoint": "https://api.example.com"},
        )
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid
        print(f"✅ PASS - 有效配置验证通过")

        return True
    except Exception as e:
        print(f"❌ FAIL - {str(e)}")
        return False


def main():
    """运行所有 Phase 3 烟雾测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " Phase 3: ExternalApiCollector 烟雾测试 ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")

    tests = [
        test_1_create_collector,
        test_2_factory_creates_external_api,
        test_3_external_api_in_capabilities,
        test_4_api_call_with_mock,
        test_5_generate_missing_ids,
        test_6_config_validation,
    ]

    results = []
    for test_func in tests:
        results.append(test_func())

    # 总结
    print("\n" + "=" * 60)
    print("烟雾测试总结")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"总计: {total} | 通过: {passed} | 失败: {failed}")

    if failed == 0:
        print("\n✅ Phase 3 烟雾测试全部通过！")
        return 0
    else:
        print(f"\n❌ Phase 3 烟雾测试有 {failed} 个失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
