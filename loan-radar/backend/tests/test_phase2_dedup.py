"""Phase 2: 数据去重 + last_crawled_at 测试"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.services.crawl_pipeline_service import (
    _sanitize_error_message,
    _post_already_exists,
    _comment_already_exists,
    run_monitor_source_crawl,
)
from app.models.post import Post
from app.models.comment import Comment
from app.models.monitor_source import MonitorSource
from app.core.database import SessionLocal


@pytest.fixture
def db():
    """创建测试数据库连接"""
    session = SessionLocal()
    yield session
    session.close()


class TestErrorSanitization:
    """测试错误信息脱敏"""

    def test_sanitize_cookie(self):
        """应能脱敏 Cookie"""
        error = "Error with cookie='abc123def456ghi'"
        result = _sanitize_error_message(error)
        assert "abc123" not in result
        assert "***" in result

    def test_sanitize_api_key(self):
        """应能脱敏 API Key"""
        error = "API Key: sk-12345678"
        result = _sanitize_error_message(error)
        assert "sk-12345678" not in result
        assert "***" in result

    def test_sanitize_token(self):
        """应能脱敏 Token"""
        error = "Authorization token=secret_token_here"
        result = _sanitize_error_message(error)
        assert "secret_token_here" not in result
        assert "***" in result

    def test_sanitize_url_params(self):
        """应能脱敏 URL 参数中的 key/token"""
        error = "https://api.example.com/endpoint?key=secret_key&other=value"
        result = _sanitize_error_message(error)
        assert "secret_key" not in result
        assert "***" in result

    def test_sanitize_multiple_sensitive_data(self):
        """应能脱敏多个敏感数据"""
        error = "Failed: cookie=abc token=xyz api_key=123"
        result = _sanitize_error_message(error)
        assert "abc" not in result
        assert "xyz" not in result
        assert "123" not in result

    def test_sanitize_preserves_non_sensitive_data(self):
        """应保留非敏感数据"""
        error = "Failed to connect to source_id=123, source_type=keyword"
        result = _sanitize_error_message(error)
        assert "source_id=123" in result
        assert "source_type=keyword" in result


class TestPostDeduplication:
    """测试 Post 去重"""

    def test_post_already_exists(self, db):
        """应能检测已存在的 post"""
        # 创建一个 post
        post = Post(
            platform="xhs",
            source_id=1,
            source_type="keyword",
            post_id="post123",
        )
        db.add(post)
        db.commit()

        # 检查是否存在
        exists = _post_already_exists(db, "xhs", "post123")
        assert exists is True

    def test_post_not_exists(self, db):
        """应能检测不存在的 post"""
        exists = _post_already_exists(db, "xhs", "nonexistent")
        assert exists is False

    def test_post_different_platform_not_exists(self, db):
        """不同平台的 post 应视为不同记录"""
        post = Post(
            platform="xhs",
            source_id=1,
            source_type="keyword",
            post_id="post123",
        )
        db.add(post)
        db.commit()

        # 在 douyin 平台上相同 post_id 应被视为不存在
        exists = _post_already_exists(db, "douyin", "post123")
        assert exists is False

    def test_post_same_id_different_platform_both_exist(self, db):
        """同一 post_id 在不同平台可以都存在"""
        post1 = Post(
            platform="xhs",
            source_id=1,
            source_type="keyword",
            post_id="post123",
        )
        post2 = Post(
            platform="douyin",
            source_id=2,
            source_type="keyword",
            post_id="post123",
        )
        db.add(post1)
        db.add(post2)
        db.commit()

        # 检查两个平台上都存在
        assert _post_already_exists(db, "xhs", "post123") is True
        assert _post_already_exists(db, "douyin", "post123") is True


class TestCommentDeduplication:
    """测试 Comment 去重"""

    def test_comment_already_exists(self, db):
        """应能检测已存在的 comment"""
        comment = Comment(
            platform="xhs",
            post_id="post123",
            comment_id="comment456",
        )
        db.add(comment)
        db.commit()

        exists = _comment_already_exists(db, "xhs", "comment456")
        assert exists is True

    def test_comment_not_exists(self, db):
        """应能检测不存在的 comment"""
        exists = _comment_already_exists(db, "xhs", "nonexistent")
        assert exists is False

    def test_comment_different_platform_not_exists(self, db):
        """不同平台的 comment 应视为不同记录"""
        comment = Comment(
            platform="xhs",
            post_id="post123",
            comment_id="comment456",
        )
        db.add(comment)
        db.commit()

        exists = _comment_already_exists(db, "douyin", "comment456")
        assert exists is False

    def test_comment_same_id_different_platform_both_exist(self, db):
        """同一 comment_id 在不同平台可以都存在"""
        comment1 = Comment(
            platform="xhs",
            post_id="post123",
            comment_id="comment456",
        )
        comment2 = Comment(
            platform="douyin",
            post_id="post789",
            comment_id="comment456",
        )
        db.add(comment1)
        db.add(comment2)
        db.commit()

        assert _comment_already_exists(db, "xhs", "comment456") is True
        assert _comment_already_exists(db, "douyin", "comment456") is True


class TestLastCrawledAtUpdate:
    """测试 last_crawled_at 更新
    
    这个测试需要完整的采集流程，包括数据库迁移。
    在烟雾测试中可以验证。
    """

    def test_monitor_source_last_crawled_at_is_nullable(self, db):
        """MonitorSource.last_crawled_at 应为 null（初始）"""
        source = MonitorSource(
            source_type="keyword",
            platform="xhs",
            name="test",
            value="test_value",
            enabled=True,
        )
        db.add(source)
        db.commit()

        # 刷新并检查
        db.refresh(source)
        assert source.last_crawled_at is None

    def test_monitor_source_last_crawled_at_update(self, db):
        """应能更新 last_crawled_at"""
        source = MonitorSource(
            source_type="keyword",
            platform="xhs",
            name="test",
            value="test_value",
            enabled=True,
        )
        db.add(source)
        db.commit()

        # 更新 last_crawled_at
        now = datetime.now(timezone.utc)
        source.last_crawled_at = now
        db.add(source)
        db.commit()

        # 刷新并检查
        db.refresh(source)
        assert source.last_crawled_at is not None
        # 允许一些时间差
        assert abs((source.last_crawled_at - now).total_seconds()) < 1
