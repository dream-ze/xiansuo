from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete

from app.collectors.base import CollectedComment, CollectedPost, CollectorResult
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.comment import Comment
from app.models.crawl_task import CrawlTask
from app.models.lead import Lead
from app.models.monitor_source import MonitorSource
from app.models.pending_competitor import PendingCompetitorAccount
from app.models.post import Post
from app.models.user import User
from app.models.login_session import LoginSession


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(db_cleanup):
    user = User(username="testuser", password_hash=hash_password("testpass123"))
    db_cleanup.add(user)
    db_cleanup.commit()
    db_cleanup.refresh(user)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_cleanup():
    session = SessionLocal()
    session.execute(delete(Lead))
    session.execute(delete(Comment))
    session.execute(delete(Post))
    session.execute(delete(PendingCompetitorAccount))
    session.execute(delete(CrawlTask))
    session.execute(delete(MonitorSource))
    session.execute(delete(LoginSession))
    session.execute(delete(User))
    session.commit()
    yield session
    session.execute(delete(Lead))
    session.execute(delete(Comment))
    session.execute(delete(Post))
    session.execute(delete(PendingCompetitorAccount))
    session.execute(delete(CrawlTask))
    session.execute(delete(MonitorSource))
    session.execute(delete(LoginSession))
    session.execute(delete(User))
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


@pytest.mark.skip(reason="mock/service session isolation issue - needs rework")
def test_collection_task_keyword_run_creates_posts_comments_and_leads(client, db_cleanup, auth_headers):
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
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        with patch("app.services.task_queue.CrawlTaskQueue.enqueue", return_value=1):
            run_response = client.post(f"/api/collection/tasks/{task_id}/run", headers=auth_headers)
            assert run_response.status_code == 202

        from app.services.collection_task_service import run_collection_task_by_id
        from app.core.database import SessionLocal
        exec_db = SessionLocal()
        try:
            run_collection_task_by_id(exec_db, task_id)
        finally:
            exec_db.close()

    session = db_cleanup
    assert session.query(Post).count() == 1
    assert session.query(Comment).count() == 1
    assert session.query(Lead).count() == 1


@pytest.mark.skip(reason="mock/service session isolation issue - needs rework")
def test_collection_task_run_account_branch(client, db_cleanup, auth_headers):
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
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        with patch("app.services.task_queue.CrawlTaskQueue.enqueue", return_value=1):
            run_response = client.post(f"/api/collection/tasks/{task_id}/run", headers=auth_headers)
            assert run_response.status_code == 202

        from app.services.collection_task_service import run_collection_task_by_id
        from app.core.database import SessionLocal
        exec_db = SessionLocal()
        try:
            run_collection_task_by_id(exec_db, task_id)
        finally:
            exec_db.close()

    session = db_cleanup
    assert session.query(Post).filter(Post.post_id == "account-note-1").count() == 1


@pytest.mark.skip(reason="mock/service session isolation issue - needs rework")
def test_collection_task_run_post_url_branch(client, db_cleanup, auth_headers):
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
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["id"]

        with patch("app.services.task_queue.CrawlTaskQueue.enqueue", return_value=1):
            run_response = client.post(f"/api/collection/tasks/{task_id}/run", headers=auth_headers)
            assert run_response.status_code == 202

        from app.services.collection_task_service import run_collection_task_by_id
        from app.core.database import SessionLocal
        exec_db = SessionLocal()
        try:
            run_collection_task_by_id(exec_db, task_id)
        finally:
            exec_db.close()

    session = db_cleanup
    assert session.query(Post).filter(Post.post_id == "post-url-note-1").count() == 1


def test_collection_task_unsupported_platform_rejected_at_create(client, db_cleanup, auth_headers):
    create_response = client.post(
        "/api/collection/tasks",
        json={
            "platform": "kuaishou",
            "source_type": "keyword",
            "source_value": "征信花了",
            "limit_count": 1,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 400
    assert "当前 MVP 仅支持 xhs/douyin/zhihu" in create_response.json()["message"]


@pytest.mark.parametrize("platform", ["bilibili", "weibo", "tieba", "other"])
def test_collection_task_other_unsupported_platforms_rejected(client, db_cleanup, auth_headers, platform):
    create_response = client.post(
        "/api/collection/tasks",
        json={
            "platform": platform,
            "source_type": "keyword",
            "source_value": "测试",
            "limit_count": 1,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 400
    assert "当前 MVP 仅支持 xhs/douyin/zhihu" in create_response.json()["message"]


@pytest.mark.skip(reason="mock/service session isolation issue - needs rework")
def test_monitor_source_crawl_media_crawler_keyword(client, db_cleanup, auth_headers):
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
            headers=auth_headers,
        )
        assert source_resp.status_code == 200
        source_id = source_resp.json()["data"]["id"]

        with patch("app.services.task_queue.CrawlTaskQueue.enqueue", return_value=1):
            crawl_resp = client.post(f"/api/monitor-sources/{source_id}/crawl", headers=auth_headers)
            assert crawl_resp.status_code == 202
            task_id = crawl_resp.json()["data"]["id"]

        from app.core.database import SessionLocal
        from app.models.crawl_task import CrawlTask
        from app.models.monitor_source import MonitorSource
        from app.services.crawl_pipeline_service import run_monitor_source_crawl
        exec_db = SessionLocal()
        try:
            task = exec_db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
            source = exec_db.query(MonitorSource).filter(MonitorSource.id == source_id).first()
            if task and source:
                run_monitor_source_crawl(exec_db, source, crawl_task=task)
        finally:
            exec_db.close()

    session = db_cleanup
    assert session.query(Post).filter(Post.source_id == source_id).count() >= 1
    assert session.query(Comment).count() >= 1


@pytest.mark.parametrize("platform", ["kuaishou", "bilibili", "weibo", "tieba", "other"])
def test_monitor_source_unsupported_platform_rejected(client, db_cleanup, auth_headers, platform):
    source_resp = client.post(
        "/api/monitor-sources",
        json={
            "source_type": "keyword",
            "platform": platform,
            "name": "不支持的平台",
            "value": "测试",
            "config": {
                "collector_type": "media_crawler",
                "login_type": "qrcode",
            },
            "enabled": True,
        },
        headers=auth_headers,
    )
    assert source_resp.status_code == 400
    assert "当前 MVP 仅支持 xhs/douyin/zhihu" in source_resp.json()["message"]


def _create_test_lead(db):
    from app.models.monitor_source import MonitorSource as MS

    source = MS(
        source_type="keyword",
        platform="xhs",
        name="线索状态测试源",
        value="征信花了",
        config={"collector_type": "media_crawler"},
        enabled=True,
    )
    db.add(source)
    db.flush()

    lead = Lead(
        platform="xhs",
        source_id=source.id,
        source_type="keyword",
        user_name="测试用户",
        content="征信花了负债高还能贷款周转吗",
        lead_level="A",
        lead_score=85.0,
        demand_type="借款需求",
        risk_level="mid",
        evidence={"keywords": ["征信花", "负债高"]},
        reason="包含借款需求关键词",
        follow_up_script="建议跟进",
        status="new",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_lead_status_update_to_interested(client, db_cleanup, auth_headers):
    lead = _create_test_lead(db_cleanup)

    update_resp = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "interested"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["status"] == "interested"


@pytest.mark.parametrize("status", ["new", "contacted", "interested", "invalid", "converted"])
def test_lead_status_update_all_valid_statuses(client, db_cleanup, auth_headers, status):
    lead = _create_test_lead(db_cleanup)

    update_resp = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": status},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["status"] == status


def test_lead_status_update_invalid_status_rejected(client, db_cleanup, auth_headers):
    lead = _create_test_lead(db_cleanup)

    update_resp = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "qualified"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 400


def test_lead_status_update_with_notes(client, db_cleanup, auth_headers):
    lead = _create_test_lead(db_cleanup)

    update_resp = client.patch(
        f"/api/leads/{lead.id}/status",
        json={"status": "interested", "notes": "客户表示有意向"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["status"] == "interested"
    assert update_resp.json()["data"]["notes"] == "客户表示有意向"
