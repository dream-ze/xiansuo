"""Phase 3 - ExternalApiCollector 单元测试"""

import hashlib
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.collectors.config import CollectorConfig
from app.collectors.external_api_collector import ExternalApiCollector


class TestExternalApiCollectorBasic:
    """基础功能测试"""

    def test_create_collector(self):
        """测试创建 ExternalApiCollector 实例"""
        collector = ExternalApiCollector()
        assert collector is not None

    def test_config_validation_missing_endpoint(self):
        """测试配置验证 - 缺少 endpoint"""
        config = CollectorConfig(
            collector_type="external_api",
            external_api={},  # 缺少 endpoint
        )
        is_valid, msg = config.validate_for_collector_type()
        # 当 external_api 存在但缺少 endpoint 时，应该提示需要 endpoint
        assert not is_valid
        assert "endpoint" in msg or "external_api" in msg

    def test_config_validation_missing_external_api(self):
        """测试配置验证 - 缺少 external_api"""
        config = CollectorConfig(
            collector_type="external_api",
            external_api=None,  # 缺少 external_api
        )
        is_valid, msg = config.validate_for_collector_type()
        assert not is_valid
        assert "external_api" in msg


class TestExternalApiCollectorWithMocking:
    """使用 Mock 的测试"""

    @patch("app.collectors.external_api_collector.requests.post")
    def test_collect_with_valid_response(self, mock_post):
        """测试采集 - 正常 API 响应"""
        # 模拟 API 响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {
                    "post_id": "post_123",
                    "title": "Test Post",
                    "content": "This is a test post",
                    "author_name": "John",
                    "like_count": 100,
                    "comment_count": 10,
                },
            ],
            "comments": [
                {
                    "post_id": "post_123",
                    "comment_id": "cmt_456",
                    "content": "Great post!",
                    "user_name": "Jane",
                    "like_count": 5,
                },
            ],
        }
        mock_post.return_value = mock_response

        # 设置环境变量
        os.environ["TEST_API_KEY"] = "test_key_123"

        # 创建 source
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

        # 执行采集
        collector = ExternalApiCollector()
        result = collector.collect(source)

        # 断言
        assert result is not None
        assert len(result.posts) == 1
        assert result.posts[0].post_id == "post_123"
        assert result.posts[0].title == "Test Post"
        assert result.posts[0].author_name == "John"
        assert len(result.comments) == 1
        assert result.comments[0].comment_id == "cmt_456"
        assert result.comments[0].content == "Great post!"

    @patch("app.collectors.external_api_collector.requests.post")
    def test_collect_generate_missing_ids(self, mock_post):
        """测试采集 - 生成缺失的 ID"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {
                    # 缺少 post_id
                    "title": "Post Without ID",
                    "content": "Content here",
                    "author_name": "Alice",
                },
            ],
            "comments": [
                {
                    "post_id": "post_123",
                    # 缺少 comment_id
                    "content": "A comment",
                    "user_name": "Bob",
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

        # 应该生成 post_id
        assert result.posts[0].post_id is not None
        assert len(result.posts[0].post_id) == 16  # SHA1 的前 16 位
        # 应该生成 comment_id
        assert result.comments[0].comment_id is not None
        assert len(result.comments[0].comment_id) == 16

    @patch("app.collectors.external_api_collector.requests.post")
    def test_collect_api_key_from_env(self, mock_post):
        """测试从环境变量读取 API 密钥"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"posts": [], "comments": []}
        mock_post.return_value = mock_response

        os.environ["MY_API_KEY_TOKEN"] = "secret_token_xyz"

        source = SimpleNamespace(
            platform="test_platform",
            config={
                "collector_type": "external_api",
                "external_api": {
                    "endpoint": "https://api.example.com/collect",
                    "api_key_env": "MY_API_KEY_TOKEN",
                },
                "max_posts": 5,
                "max_comments_per_post": 20,
                "timeout_seconds": 30,
                "retry_times": 1,
                "rate_limit_seconds": 0,
            },
        )

        collector = ExternalApiCollector()
        result = collector.collect(source)

        # 验证请求头中包含 Authorization Bearer
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer secret_token_xyz"

    @patch("app.collectors.external_api_collector.requests.post")
    def test_collect_missing_api_key_env(self, mock_post):
        """测试缺少 API 密钥环境变量"""
        # 确保环境变量不存在
        if "MISSING_API_KEY" in os.environ:
            del os.environ["MISSING_API_KEY"]

        source = SimpleNamespace(
            platform="test_platform",
            config={
                "collector_type": "external_api",
                "external_api": {
                    "endpoint": "https://api.example.com/collect",
                    "api_key_env": "MISSING_API_KEY",
                },
                "max_posts": 5,
                "max_comments_per_post": 20,
                "timeout_seconds": 30,
                "retry_times": 1,
                "rate_limit_seconds": 0,
            },
        )

        collector = ExternalApiCollector()
        with pytest.raises(ValueError, match="not set"):
            collector.collect(source)


class TestExternalApiCollectorRetry:
    """重试机制测试"""

    @patch("app.collectors.external_api_collector.requests.post")
    @patch("app.collectors.external_api_collector.time.sleep")
    def test_retry_on_failure(self, mock_sleep, mock_post):
        """测试 API 失败重试"""
        import requests

        # 第一次失败，第二次成功
        mock_response = MagicMock()
        mock_response.json.return_value = {"posts": [], "comments": []}
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            mock_response,
        ]

        os.environ["TEST_API_KEY"] = "test_key_123"

        source = SimpleNamespace(
            platform="test_platform",
            config={
                "collector_type": "external_api",
                "external_api": {
                    "endpoint": "https://api.example.com/collect",
                    "api_key_env": "TEST_API_KEY",
                },
                "max_posts": 5,
                "max_comments_per_post": 20,
                "timeout_seconds": 30,
                "retry_times": 3,
                "rate_limit_seconds": 0,
            },
        )

        collector = ExternalApiCollector()
        result = collector.collect(source)

        # 应该重试了
        assert mock_post.call_count == 2
        assert result is not None

    @patch("app.collectors.external_api_collector.requests.post")
    def test_all_retries_fail(self, mock_post):
        """测试所有重试均失败"""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        os.environ["TEST_API_KEY"] = "test_key_123"

        source = SimpleNamespace(
            platform="test_platform",
            config={
                "collector_type": "external_api",
                "external_api": {
                    "endpoint": "https://api.example.com/collect",
                    "api_key_env": "TEST_API_KEY",
                },
                "max_posts": 5,
                "max_comments_per_post": 20,
                "timeout_seconds": 30,
                "retry_times": 2,
                "rate_limit_seconds": 0,
            },
        )

        collector = ExternalApiCollector()
        with pytest.raises(Exception, match="failed after"):
            collector.collect(source)


class TestExternalApiParseResponse:
    """响应解析测试"""

    @patch("app.collectors.external_api_collector.requests.post")
    def test_parse_response_with_metadata(self, mock_post):
        """测试解析 API 响应元数据"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {
                    "post_id": "p1",
                    "title": "Post 1",
                    "content": "Content 1",
                    "author_name": "Author 1",
                    "like_count": 100,
                    "comment_count": 5,
                    "collect_count": 10,
                    "is_hot": True,
                },
            ],
            "comments": [],
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

        assert result.metadata is not None
        assert result.metadata["source"] == "external_api"
        assert result.metadata["total_posts"] == 1
        assert result.metadata["total_comments"] == 0

    @patch("app.collectors.external_api_collector.requests.post")
    def test_parse_response_handles_malformed_data(self, mock_post):
        """测试处理格式不正确的数据"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "posts": [
                {"post_id": "p1", "title": "Valid Post"},
                {"title": "Invalid Post", "like_count": "not_a_number"},  # 格式不正确
            ],
            "comments": [
                {"post_id": "p1", "comment_id": "c1", "content": "Valid Comment"},
                {
                    "post_id": "p1",
                    # 缺少 content
                    "content": None,
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

        # 应该跳过格式不正确的数据
        assert len(result.posts) >= 1  # 至少有一个有效的
        assert len(result.comments) >= 1  # 至少有一个有效的


class TestExternalApiFactoryIntegration:
    """CollectorFactory 集成测试"""

    def test_factory_creates_external_api_collector(self):
        """测试 CollectorFactory 能创建 ExternalApiCollector"""
        from app.collectors.factory import CollectorFactory

        os.environ["TEST_API_KEY"] = "test_key"

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

    def test_external_api_in_supported_collectors(self):
        """测试 external_api 在能力列表中显示为 ready"""
        from app.collectors.factory import CollectorFactory

        supported = CollectorFactory.get_supported_collectors()
        assert "external_api" in supported
        assert supported["external_api"]["status"] == "ready"
