"""Phase 2: 数据去重 + last_crawled_at 测试"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.services.crawl_pipeline_service import (
    _sanitize_error_message,
    run_monitor_source_crawl,
)
from app.services.dedup_service import (
    batch_dedup_posts,
    batch_dedup_comments,
)
from app.models.post import Post
from app.models.comment import Comment
from app.models.monitor_source import MonitorSource
from app.core.database import SessionLocal


@pytest.fixture
def db():
    """创建测试数据库连接"""
    session = SessionLocal()
    # 每次用例前先清理相关表，避免历史测试数据导致唯一约束冲突。
    session.execute(delete(Comment))
    session.execute(delete(Post))
    session.execute(delete(MonitorSource))
    session.commit()
    yield session
    session.execute(delete(Comment))
    session.execute(delete(Post))
    session.execute(delete(MonitorSource))
    session.commit()
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
        post = Post(
            platform="xhs",
            source_id=1,
            source_type="keyword",
            post_id="post123",
        )
        db.add(post)
        db.commit()

        from app.collectors.base import CollectedPost
        collected = [CollectedPost(platform="xhs", post_id="post123")]
        new_posts, updated_posts, dup_post_ids, _, _ = batch_dedup_posts(db, "xhs", collected)
        assert len(new_posts) == 0
        assert len(updated_posts) == 1
        assert "post123" in dup_post_ids

    def test_post_not_exists(self, db):
        """应能检测不存在的 post"""
        from app.collectors.base import CollectedPost
        collected = [CollectedPost(platform="xhs", post_id="nonexistent")]
        new_posts, _, _, dup_count, _ = batch_dedup_posts(db, "xhs", collected)
        assert len(new_posts) == 1
        assert dup_count == 0

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

        from app.collectors.base import CollectedPost
        collected = [CollectedPost(platform="douyin", post_id="post123")]
        new_posts, _, _, dup_count, _ = batch_dedup_posts(db, "douyin", collected)
        assert len(new_posts) == 1
        assert dup_count == 0

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

        from app.collectors.base import CollectedPost
        xhs_collected = [CollectedPost(platform="xhs", post_id="post123")]
        douyin_collected = [CollectedPost(platform="douyin", post_id="post123")]
        new_xhs, updated_xhs, dup_xhs_ids, _, _ = batch_dedup_posts(db, "xhs", xhs_collected)
        new_douyin, updated_douyin, dup_douyin_ids, _, _ = batch_dedup_posts(db, "douyin", douyin_collected)
        assert len(new_xhs) == 0
        assert len(updated_xhs) == 1
        assert "post123" in dup_xhs_ids
        assert len(new_douyin) == 0
        assert len(updated_douyin) == 1
        assert "post123" in dup_douyin_ids


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

        from app.collectors.base import CollectedComment
        collected = [CollectedComment(platform="xhs", post_id="post123", comment_id="comment456")]
        new_comments, dup_count = batch_dedup_comments(db, "xhs", collected, set())
        assert len(new_comments) == 0
        assert dup_count >= 1

    def test_comment_not_exists(self, db):
        """应能检测不存在的 comment"""
        from app.collectors.base import CollectedComment
        collected = [CollectedComment(platform="xhs", post_id="post123", comment_id="nonexistent")]
        new_comments, dup_count = batch_dedup_comments(db, "xhs", collected, set())
        assert len(new_comments) == 1
        assert dup_count == 0

    def test_comment_different_platform_not_exists(self, db):
        """不同平台的 comment 应视为不同记录"""
        comment = Comment(
            platform="xhs",
            post_id="post123",
            comment_id="comment456",
        )
        db.add(comment)
        db.commit()

        from app.collectors.base import CollectedComment
        collected = [CollectedComment(platform="douyin", post_id="post123", comment_id="comment456")]
        new_comments, dup_count = batch_dedup_comments(db, "douyin", collected, set())
        assert len(new_comments) == 1
        assert dup_count == 0

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

        from app.collectors.base import CollectedComment
        xhs_collected = [CollectedComment(platform="xhs", post_id="post123", comment_id="comment456")]
        douyin_collected = [CollectedComment(platform="douyin", post_id="post789", comment_id="comment456")]
        new_xhs, dup_xhs = batch_dedup_comments(db, "xhs", xhs_collected, set())
        new_douyin, dup_douyin = batch_dedup_comments(db, "douyin", douyin_collected, set())
        assert len(new_xhs) == 0
        assert dup_xhs >= 1
        assert len(new_douyin) == 0
        assert dup_douyin >= 1


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
