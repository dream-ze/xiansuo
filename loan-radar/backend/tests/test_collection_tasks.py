from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete

from app.collectors.base import CollectedComment, CollectedPost, CollectorResult
from app.core.database import SessionLocal
from app.main import app
from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.pending_competitor import PendingCompetitorAccount
from app.models.post import Post


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_cleanup():
    session = SessionLocal()
    session.execute(delete(Lead))
    session.execute(delete(Comment))
    session.execute(delete(Post))
    session.execute(delete(PendingCompetitorAccount))
    session.execute(delete(CrawlTask))
    session.execute(delete(MonitorSource))
    session.commit()
    yield session
    session.execute(delete(Lead))
    session.execute(delete(Comment))
    session.execute(delete(Post))
    session.execute(delete(PendingCompetitorAccount))
    session.execute(delete(CrawlTask))
    session.execute(delete(MonitorSource))
    session.commit()
    session.close()


def _make_fake_collector_result(
    posts=None,
    comments=None,
) -> CollectorResult:
    if posts is None:
        posts = [
            CollectedPost(
                platform="xhs",
                post_id="note-1",
                title="征信花了还能贷款吗",
                content="征信查询多，想找能做的渠道",
                post_url="https://www.xiaohongshu.com/explore/note-1",
                author_name="助贷顾问A",
                author_profile_url="https://www.xiaohongshu.com/user/profile/user-a",
                like_count=120,
                comment_count=18,
                collect_count=36,
                is_hot=True,
            )
        ]
    if comments is None:
        comments = [
            CollectedComment(
                platform="xhs",
                post_id="note-1",
                comment_id="comment-1",
                user_name="求助用户",
                user_profile_url="https://www.xiaohongshu.com/user/profile/demand-user",
                content="征信花了负债高还能贷款周转吗",
                like_count=3,
            )
        ]
    return CollectorResult(posts=posts, comments=comments)


def _mock_media_crawler_collector(fake_result):
    mock_instance = MagicMock()
    mock_instance.collect.return_value = fake_result
    mock_cls = MagicMock(return_value=mock_instance)
    return mock_cls, mock_instance


def test_collection_task_keyword_run_creates_posts_comments_and_leads(client, db_cleanup):
    fake_result = _make_fake_collector_result()
    mock_cls, mock_instance = _mock_media_crawler_collector(fake_result)

    with patch("app.collectors.media_crawler.collector.MediaCrawlerCollector", mock_cls):
        create_response = client.post(
            "/api/collection/tasks",
            json={
                "platform": "xhs",
                "source_type": "keyword",
                "source_value": "征信花了",
                "limit_count": 2,
            },
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        run_response = client.post(f"/api/collection/tasks/{task_id}/run")
        assert run_response.status_code == 200
        payload = run_response.json()["data"]
        assert payload["status"] == "success"
        assert payload["collected_posts"] == 1
        assert payload["collected_comments"] == 1
        assert payload["post_count"] == 1
        assert payload["comment_count"] == 1
        assert payload["lead_count"] == 1

    session = db_cleanup
    assert session.query(Post).count() == 1
    assert session.query(Comment).count() == 1
    assert session.query(Lead).count() == 1


def test_collection_task_run_account_branch(client, db_cleanup):
    fake_result = _make_fake_collector_result(
        posts=[
            CollectedPost(
                platform="xhs",
                post_id="account-note-1",
                title="账号主页笔记",
                content="账号维度采集测试",
                post_url="https://www.xiaohongshu.com/user/profile/test-account",
                author_name="账号作者",
                author_profile_url="https://www.xiaohongshu.com/user/profile/test-account",
            )
        ],
        comments=[
            CollectedComment(
                platform="xhs",
                post_id="account-note-1",
                comment_id="comment-account-1",
                user_name="求助用户",
                user_profile_url="https://www.xiaohongshu.com/user/profile/demand-user",
                content="征信花了负债高还能贷款周转吗",
                like_count=3,
            )
        ],
    )
    mock_cls, _ = _mock_media_crawler_collector(fake_result)

    with patch("app.collectors.media_crawler.collector.MediaCrawlerCollector", mock_cls):
        create_response = client.post(
            "/api/collection/tasks",
            json={
                "platform": "xhs",
                "source_type": "account",
                "source_value": "https://www.xiaohongshu.com/user/profile/test-account",
                "limit_count": 2,
            },
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        run_response = client.post(f"/api/collection/tasks/{task_id}/run")
        assert run_response.status_code == 200
        payload = run_response.json()["data"]
        assert payload["status"] == "success"
        assert payload["post_count"] == 1
        assert payload["comment_count"] == 1

    session = db_cleanup
    assert session.query(Post).filter(Post.post_id == "account-note-1").count() == 1


def test_collection_task_run_post_url_branch(client, db_cleanup):
    fake_result = _make_fake_collector_result(
        posts=[
            CollectedPost(
                platform="xhs",
                post_id="post-url-note-1",
                title="单贴采集",
                content="post_url 采集测试",
                post_url="https://www.xiaohongshu.com/explore/post-url-note-1",
                author_name="单贴作者",
                author_profile_url="https://www.xiaohongshu.com/user/profile/post-url-author",
            )
        ],
        comments=[
            CollectedComment(
                platform="xhs",
                post_id="post-url-note-1",
                comment_id="comment-post-url-1",
                user_name="求助用户",
                user_profile_url="https://www.xiaohongshu.com/user/profile/demand-user",
                content="征信花了负债高还能贷款周转吗",
                like_count=3,
            )
        ],
    )
    mock_cls, _ = _mock_media_crawler_collector(fake_result)

    with patch("app.collectors.media_crawler.collector.MediaCrawlerCollector", mock_cls):
        create_response = client.post(
            "/api/collection/tasks",
            json={
                "platform": "xhs",
                "source_type": "post_url",
                "source_value": "https://www.xiaohongshu.com/explore/post-url-note-1",
                "limit_count": 1,
            },
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        run_response = client.post(f"/api/collection/tasks/{task_id}/run")
        assert run_response.status_code == 200
        payload = run_response.json()["data"]
        assert payload["status"] == "success"
        assert payload["post_count"] == 1
        assert payload["comment_count"] == 1

    session = db_cleanup
    assert session.query(Post).filter(Post.post_id == "post-url-note-1").count() == 1


def test_collection_task_unsupported_platform_marks_failed(client, db_cleanup):
    create_response = client.post(
        "/api/collection/tasks",
        json={
            "platform": "unsupported_platform",
            "source_type": "keyword",
            "source_value": "征信花了",
            "limit_count": 1,
        },
    )
    assert create_response.status_code == 200
    task_id = create_response.json()["data"]["id"]

    run_response = client.post(f"/api/collection/tasks/{task_id}/run")
    assert run_response.status_code == 200
    payload = run_response.json()["data"]
    assert payload["status"] == "failed"
    assert payload.get("error_message")


def test_monitor_source_crawl_media_crawler_keyword(client, db_cleanup):
    fake_result = _make_fake_collector_result()
    mock_cls, _ = _mock_media_crawler_collector(fake_result)

    with patch("app.collectors.media_crawler.collector.MediaCrawlerCollector", mock_cls):
        source_resp = client.post(
            "/api/monitor-sources",
            json={
                "source_type": "keyword",
                "platform": "xhs",
                "name": "关键词真实采集",
                "value": "征信花了",
                "config": {
                    "collector_type": "media_crawler",
                    "login_type": "cookie",
                    "cookies": "session=masked",
                    "max_posts": 2,
                },
                "enabled": True,
            },
        )
        assert source_resp.status_code == 200
        source_id = source_resp.json()["data"]["id"]

        crawl_resp = client.post(f"/api/monitor-sources/{source_id}/crawl")
        assert crawl_resp.status_code == 200
        payload = crawl_resp.json()["data"]

        assert payload["status"] == "success"
        assert payload["post_count"] == 1
        assert payload["comment_count"] == 1
        assert payload["lead_count"] == 1

    session = db_cleanup
    assert session.query(Post).filter(Post.source_id == source_id).count() >= 1
    assert session.query(Comment).count() >= 1
