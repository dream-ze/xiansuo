from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.collectors.base import CollectionRequestError
from app.collectors.xhs_metrics import DriverMetricsRecorder
from app.collectors.xhs_provider import XhsProvider
from app.collectors.xhs_spider_adapter import SpiderXhsAdapter


def _prepare_fake_spider_repo(tmp_path: Path) -> Path:
    api_dir = tmp_path / "apis"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "__init__.py").write_text("", encoding="utf-8")
    (api_dir / "xhs_pc_apis.py").write_text(
        """
class XHS_Apis:
    def search_some_note(self, keyword, limit, cookies, proxies=None):
        return True, "ok", [
            {
                "id": "spider-note-1",
                "xsec_token": "spider-token-1",
                "note_card": {
                    "title": keyword,
                    "desc": "spider search result"
                }
            }
        ]

    def get_note_info(self, post_url, cookies, proxies=None):
        return True, "ok", {
            "data": {
                "items": [
                    {
                        "id": "spider-note-1",
                        "url": post_url,
                        "xsec_token": "spider-token-1",
                        "note_card": {
                            "title": "spider detail",
                            "desc": "spider detail content"
                        }
                    }
                ]
            }
        }

    def get_note_all_comment(self, post_url, cookies, proxies=None):
        return True, "ok", [
            {
                "id": "comment-1",
                "note_id": "spider-note-1",
                "content": "main comment",
                "sub_comments": [
                    {
                        "id": "comment-1-1",
                        "note_id": "spider-note-1",
                        "content": "reply"
                    }
                ]
            }
        ]
        """.strip(),
        encoding="utf-8",
    )
    return tmp_path


def test_spider_adapter_dynamic_import_and_full_chain(tmp_path, monkeypatch):
    spider_repo = _prepare_fake_spider_repo(tmp_path)
    monkeypatch.setenv("XHS_SPIDER_PATH", str(spider_repo))

    adapter = SpiderXhsAdapter(cookies="a1=test-cookie")

    notes = adapter.search_notes(keyword="征信花了", limit=1)
    assert len(notes) == 1

    post_url = "https://www.xiaohongshu.com/explore/spider-note-1"
    detail = adapter.get_note_detail(post_url=post_url)
    assert detail["id"] == "spider-note-1"
    assert detail["url"] == post_url

    comments = adapter.get_note_comments(post_url=post_url, limit=5)
    # Includes flattened sub comments
    assert len(comments) == 2


def test_xhs_provider_spider_keyword_to_detail_to_comments(tmp_path, monkeypatch):
    spider_repo = _prepare_fake_spider_repo(tmp_path)
    monkeypatch.setenv("XHS_COOKIES", "a1=test-cookie")
    monkeypatch.setenv("XHS_PROVIDER_DRIVER", "spider")
    monkeypatch.setenv("XHS_PROVIDER_FALLBACK_TO_PC", "false")
    monkeypatch.setenv("XHS_SPIDER_PATH", str(spider_repo))

    metrics = DriverMetricsRecorder()
    provider = XhsProvider(metrics_recorder=metrics)

    keyword_result = provider.collect_by_keyword("征信花了", 1)
    assert len(keyword_result.posts) == 1
    post = keyword_result.posts[0]
    assert post.post_id == "spider-note-1"

    comments = provider.collect_comments(
        post_id=post.post_id,
        post_url=post.post_url or "",
        xsec_token="spider-token-1",
        limit=10,
    )
    assert len(comments) == 2

    snapshot = metrics.snapshot()
    assert snapshot["spider"]["keyword_search"]["success"] == 1
    assert snapshot["spider"]["note_detail"]["success"] >= 1
    assert snapshot["spider"]["note_comments"]["success"] == 1


@pytest.mark.online
@pytest.mark.skipif(
    os.getenv("RUN_XHS_SPIDER_ONLINE", "").lower() not in {"1", "true", "yes"},
    reason="set RUN_XHS_SPIDER_ONLINE=1 to enable online Spider_XHS integration test",
)
def test_spider_adapter_online_smoke(monkeypatch):
    spider_path = (os.getenv("XHS_SPIDER_PATH") or "").strip()
    cookies = (os.getenv("XHS_COOKIES") or "").strip()

    if not spider_path:
        pytest.skip("XHS_SPIDER_PATH is required for online test")
    if not cookies:
        pytest.skip("XHS_COOKIES is required for online test")

    adapter = SpiderXhsAdapter(cookies=cookies, spider_path=spider_path)

    try:
        notes = adapter.search_notes(keyword="贷款", limit=1)
    except CollectionRequestError as error:
        pytest.fail(f"online spider search failed: {error}")

    assert isinstance(notes, list)
