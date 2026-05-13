from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete

from app.collectors.base import CollectedComment, CollectedPost, ProviderCollectionResult
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


class FakeXhsProvider:
    account_called = False
    post_url_called = False

    def __init__(self, *args, **kwargs):
        pass

    def close(self):
        return None

    def collect_by_keyword(self, keyword: str, limit: int) -> ProviderCollectionResult:
        assert keyword == "征信花了"
        assert limit == 2
        return ProviderCollectionResult(
            posts=[
                CollectedPost(
                    platform="xhs",
                    post_id="note-1",
                    title="征信花了还能贷款吗",
                    content="征信查询多，想找能做的渠道",
                    post_url="https://www.xiaohongshu.com/explore/note-1?xsec_token=test-token",
                    author_name="助贷顾问A",
                    author_profile_url="https://www.xiaohongshu.com/user/profile/user-a",
                    like_count=120,
                    comment_count=18,
                    collect_count=36,
                    is_hot=True,
                    raw_data={"xsec_token": "test-token"},
                )
            ],
            metadata={"entry": "keyword"},
        )

    def collect_by_account(self, account_url: str, limit: int) -> ProviderCollectionResult:
        self.__class__.account_called = True
        return ProviderCollectionResult(
            posts=[
                CollectedPost(
                    platform="xhs",
                    post_id="account-note-1",
                    title="账号主页笔记",
                    content="账号维度采集测试",
                    post_url=account_url,
                    author_name="账号作者",
                    author_profile_url=account_url,
                    raw_data={"xsec_token": "account-token"},
                )
            ],
            metadata={"entry": "account"},
        )

    def collect_by_post_url(self, post_url: str) -> ProviderCollectionResult:
        self.__class__.post_url_called = True
        return ProviderCollectionResult(
            posts=[
                CollectedPost(
                    platform="xhs",
                    post_id="post-url-note-1",
                    title="单贴采集",
                    content="post_url 采集测试",
                    post_url=post_url,
                    author_name="单贴作者",
                    author_profile_url="https://www.xiaohongshu.com/user/profile/post-url-author",
                    raw_data={"xsec_token": "post-url-token"},
                )
            ],
            metadata={"entry": "post_url"},
        )

    def collect_comments(
        self,
        post_id: str,
        post_url: str,
        xsec_token: str,
        limit: int = 50,
    ) -> list[CollectedComment]:
        assert limit == 50
        return [
            CollectedComment(
                platform="xhs",
                post_id=post_id,
                comment_id=f"comment-{post_id}",
                user_name="求助用户",
                user_profile_url="https://www.xiaohongshu.com/user/profile/demand-user",
                content="征信花了负债高还能贷款周转吗",
                like_count=3,
                raw_data={"id": f"comment-{post_id}", "note_id": post_id},
            )
        ]


def test_collection_task_keyword_run_creates_posts_comments_and_leads(client, db_cleanup, monkeypatch):
    monkeypatch.setattr("app.services.collection_task_service.XhsProvider", FakeXhsProvider)

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


def test_collection_task_run_account_branch(client, db_cleanup, monkeypatch):
    FakeXhsProvider.account_called = False
    monkeypatch.setattr("app.services.collection_task_service.XhsProvider", FakeXhsProvider)

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
    assert FakeXhsProvider.account_called is True

    session = db_cleanup
    assert session.query(Post).filter(Post.post_id == "account-note-1").count() == 1


def test_collection_task_run_post_url_branch(client, db_cleanup, monkeypatch):
    FakeXhsProvider.post_url_called = False
    monkeypatch.setattr("app.services.collection_task_service.XhsProvider", FakeXhsProvider)

    create_response = client.post(
        "/api/collection/tasks",
        json={
            "platform": "xhs",
            "source_type": "post_url",
            "source_value": "https://www.xiaohongshu.com/explore/post-url-note-1?xsec_token=test",
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
    assert FakeXhsProvider.post_url_called is True

    session = db_cleanup
    assert session.query(Post).filter(Post.post_id == "post-url-note-1").count() == 1


def test_collection_task_missing_cookie_marks_failed(client, db_cleanup, monkeypatch):
    monkeypatch.delenv("XHS_COOKIES", raising=False)

    create_response = client.post(
        "/api/collection/tasks",
        json={
            "platform": "xhs",
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
    assert "xhs_cookies" in payload["error_message"].lower()
