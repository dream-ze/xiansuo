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
        raise AssertionError("account collection should not be used in this test")

    def collect_by_post_url(self, post_url: str) -> ProviderCollectionResult:
        raise AssertionError("post url collection should not be used in this test")

    def collect_comments(self, post_id: str, post_url: str, xsec_token: str) -> list[CollectedComment]:
        assert post_id == "note-1"
        assert xsec_token == "test-token"
        return [
            CollectedComment(
                platform="xhs",
                post_id="note-1",
                comment_id="comment-1",
                user_name="求助用户",
                user_profile_url="https://www.xiaohongshu.com/user/profile/demand-user",
                content="征信花了负债高还能贷款周转吗",
                like_count=3,
                raw_data={"id": "comment-1", "note_id": "note-1"},
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
