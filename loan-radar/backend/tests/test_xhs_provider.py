import pytest

from app.collectors.base import CollectionAuthError, CollectionRequestError
from app.collectors.xhs_metrics import DriverMetricsRecorder
from app.collectors.xhs_provider import XhsProvider


def test_xhs_provider_requires_cookies(monkeypatch):
    monkeypatch.delenv("XHS_COOKIES", raising=False)

    with pytest.raises(CollectionAuthError, match="XHS_COOKIES"):
        XhsProvider()


class FakePcClient:
    def __init__(self) -> None:
        self.keyword_called = False
        self.detail_called = False
        self.comments_called = False

    def search_notes(self, keyword: str, limit: int):
        self.keyword_called = True
        return [{"id": "pc-note-1", "note_card": {"title": keyword, "desc": "pc"}}]

    def get_note_detail(self, post_url: str):
        self.detail_called = True
        return {"id": "pc-detail-1", "url": post_url, "note_card": {"title": "pc-detail", "desc": "pc"}}

    def get_user_notes(self, account_url: str, limit: int):
        return []

    def get_note_comments(self, post_id: str, post_url: str, xsec_token: str, limit: int):
        self.comments_called = True
        return [{"id": "pc-comment-1", "note_id": post_id, "content": "pc-comment"}]

    def close(self):
        return None


class FakeSpiderAdapter:
    def __init__(self) -> None:
        self.keyword_called = False
        self.detail_called = False
        self.comments_called = False
        self.detail_calls = 0

    def search_notes(self, keyword: str, limit: int):
        self.keyword_called = True
        return [{"id": "spider-note-1", "xsec_token": "spider-token", "note_card": {"title": keyword, "desc": "spider"}}]

    def get_note_detail(self, post_url: str):
        self.detail_called = True
        self.detail_calls += 1
        return {
            "id": "spider-detail-1",
            "url": post_url,
            "note_card": {"title": "spider-detail", "desc": "spider"},
        }

    def get_note_comments(self, post_url: str, limit: int):
        self.comments_called = True
        return [{"id": "spider-comment-1", "note_id": "spider-detail-1", "content": "spider-comment"}]


class FakeCdpClient:
    def __init__(self) -> None:
        self.keyword_called = False
        self.detail_called = False
        self.comments_called = False

    def search_notes(self, keyword: str, limit: int):
        self.keyword_called = True
        return [{"id": "cdp-note-1", "note_card": {"title": keyword, "desc": "cdp"}}]

    def get_note_detail(self, post_url: str):
        self.detail_called = True
        return {"id": "cdp-detail-1", "url": post_url, "note_card": {"title": "cdp-detail", "desc": "cdp"}}

    def get_note_comments(self, post_id: str, post_url: str, xsec_token: str, limit: int):
        self.comments_called = True
        return [{"id": "cdp-comment-1", "note_id": post_id, "content": "cdp-comment"}]

    def close(self):
        return None


def test_xhs_provider_pc_driver_uses_pc_client(monkeypatch):
    monkeypatch.setenv("XHS_COOKIES", "a1=test-cookie")
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "pc")
    monkeypatch.delenv("XHS_PROVIDER_FALLBACK_TO_PC", raising=False)

    client = FakePcClient()
    provider = XhsProvider(client=client)

    posts_result = provider.collect_by_keyword("征信花了", 1)
    detail_result = provider.collect_by_post_url("https://www.xiaohongshu.com/explore/pc-detail-1")
    comments = provider.collect_comments(
        post_id="pc-detail-1",
        post_url="https://www.xiaohongshu.com/explore/pc-detail-1",
        xsec_token="",
    )

    assert len(posts_result.posts) == 1
    assert len(detail_result.posts) == 1
    assert len(comments) == 1
    assert client.keyword_called is True
    assert client.detail_called is True
    assert client.comments_called is True


def test_xhs_provider_cdp_driver_does_not_require_cookies(monkeypatch):
    monkeypatch.delenv("XHS_COOKIES", raising=False)
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "cdp")

    cdp_client = FakeCdpClient()
    provider = XhsProvider(cdp_client=cdp_client)

    result = provider.collect_by_keyword("征信花了", 1)

    assert len(result.posts) == 1
    assert result.posts[0].post_id == "cdp-note-1"
    assert cdp_client.keyword_called is True


def test_xhs_provider_cdp_driver_uses_cdp_client(monkeypatch):
    monkeypatch.delenv("XHS_COOKIES", raising=False)
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "cdp")

    cdp_client = FakeCdpClient()
    provider = XhsProvider(cdp_client=cdp_client)

    posts_result = provider.collect_by_keyword("征信花了", 1)
    detail_result = provider.collect_by_post_url("https://www.xiaohongshu.com/explore/cdp-detail-1")
    comments = provider.collect_comments(
        post_id="cdp-detail-1",
        post_url="https://www.xiaohongshu.com/explore/cdp-detail-1",
        xsec_token="",
    )

    assert len(posts_result.posts) == 1
    assert len(detail_result.posts) == 1
    assert len(comments) == 1
    assert cdp_client.keyword_called is True
    assert cdp_client.detail_called is True
    assert cdp_client.comments_called is True


class FailingCdpClient(FakeCdpClient):
    def search_notes(self, keyword: str, limit: int):
        raise CollectionRequestError("cdp connect failed token=secret web_session=secret")


def test_xhs_provider_cdp_failure_records_sanitized_request_error(monkeypatch):
    monkeypatch.delenv("XHS_COOKIES", raising=False)
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "cdp")

    recorder = DriverMetricsRecorder()
    provider = XhsProvider(cdp_client=FailingCdpClient(), metrics_recorder=recorder)

    with pytest.raises(CollectionRequestError) as exc:
        provider.collect_by_keyword("征信花了", 1)

    assert "secret" not in str(exc.value)
    snapshot = recorder.snapshot()
    assert snapshot["cdp"]["keyword_search"]["failed"] == 1
    assert snapshot["cdp"]["keyword_search"]["failure_types"]["P2.request"] == 1


def test_xhs_provider_auto_driver_falls_back_from_cdp_to_pc(monkeypatch):
    monkeypatch.setenv("XHS_COOKIES", "a1=test-cookie")
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "auto")

    client = FakePcClient()
    recorder = DriverMetricsRecorder()
    provider = XhsProvider(
        client=client,
        cdp_client=FailingCdpClient(),
        metrics_recorder=recorder,
    )

    result = provider.collect_by_keyword("征信花了", 1)

    assert len(result.posts) == 1
    assert client.keyword_called is True
    snapshot = recorder.snapshot()
    assert snapshot["cdp"]["keyword_search"]["failed"] == 1
    assert snapshot["pc"]["keyword_search"]["success"] == 1


def test_xhs_provider_spider_driver_uses_spider_adapter(monkeypatch):
    monkeypatch.setenv("XHS_COOKIES", "a1=test-cookie")
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "spider")
    monkeypatch.setenv("XHS_PROVIDER_FALLBACK_TO_PC", "false")

    client = FakePcClient()
    spider_adapter = FakeSpiderAdapter()
    provider = XhsProvider(client=client, spider_adapter=spider_adapter)

    posts_result = provider.collect_by_keyword("征信花了", 1)
    detail_result = provider.collect_by_post_url("https://www.xiaohongshu.com/explore/spider-detail-1")
    comments = provider.collect_comments(
        post_id="spider-detail-1",
        post_url="https://www.xiaohongshu.com/explore/spider-detail-1",
        xsec_token="",
    )

    assert len(posts_result.posts) == 1
    assert len(detail_result.posts) == 1
    assert len(comments) == 1
    assert spider_adapter.keyword_called is True
    assert spider_adapter.detail_called is True
    assert spider_adapter.detail_calls >= 2
    assert spider_adapter.comments_called is True
    assert client.keyword_called is False
    assert client.detail_called is False
    assert client.comments_called is False


class FailingSpiderAdapter(FakeSpiderAdapter):
    def search_notes(self, keyword: str, limit: int):
        raise CollectionRequestError("temporary spider failure")


def test_xhs_provider_spider_driver_can_fallback_to_pc(monkeypatch):
    monkeypatch.setenv("XHS_COOKIES", "a1=test-cookie")
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "spider")
    monkeypatch.setenv("XHS_PROVIDER_FALLBACK_TO_PC", "true")

    client = FakePcClient()
    spider_adapter = FailingSpiderAdapter()
    provider = XhsProvider(client=client, spider_adapter=spider_adapter)

    posts_result = provider.collect_by_keyword("征信花了", 1)

    assert len(posts_result.posts) == 1
    assert client.keyword_called is True


def test_xhs_provider_records_driver_metrics(monkeypatch):
    monkeypatch.setenv("XHS_COOKIES", "a1=test-cookie")
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "spider")
    monkeypatch.setenv("XHS_PROVIDER_FALLBACK_TO_PC", "false")

    client = FakePcClient()
    spider_adapter = FakeSpiderAdapter()
    recorder = DriverMetricsRecorder()
    provider = XhsProvider(client=client, spider_adapter=spider_adapter, metrics_recorder=recorder)

    result = provider.collect_by_keyword("征信花了", 1)
    snapshot = recorder.snapshot()

    assert len(result.posts) == 1
    assert "spider" in snapshot
    assert snapshot["spider"]["keyword_search"]["success"] == 1
    assert snapshot["spider"]["note_detail"]["success"] >= 1
    assert isinstance(result.metadata, dict)
    assert "driver_metrics" in result.metadata
