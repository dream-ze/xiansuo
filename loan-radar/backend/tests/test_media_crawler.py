"""MediaCrawler 集成测试"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.collectors.config import CollectorConfig
from app.collectors.factory import CollectorFactory
from app.collectors.media_crawler.bridge import MediaCrawlerBridge
from app.collectors.media_crawler.collector import MediaCrawlerCollector
from app.collectors.media_crawler.mappers import (
    PLATFORM_LABELS,
    SUPPORTED_PLATFORMS,
    map_platform_data,
    _parse_datetime,
    _is_hot,
)


class TestMediaCrawlerMappers:
    def test_xhs_post_mapping(self):
        raw = {
            "posts": [
                {
                    "note_id": "xhs001",
                    "title": "征信修复指南",
                    "desc": "分享征信修复经验",
                    "user": {"nickname": "小红薯", "user_id": "u001"},
                    "interact_info": {
                        "liked_count": "150",
                        "comment_count": "30",
                        "collected_count": "60",
                    },
                    "xsec_token": "tok123",
                }
            ],
            "comments": [],
        }
        posts, comments = map_platform_data(raw, "xhs")
        assert len(posts) == 1
        p = posts[0]
        assert p.post_id == "xhs001"
        assert p.title == "征信修复指南"
        assert p.content == "分享征信修复经验"
        assert p.author_name == "小红薯"
        assert p.like_count == 150
        assert p.comment_count == 30
        assert p.collect_count == 60
        assert p.is_hot is True
        assert "xsec_token=tok123" in (p.post_url or "")

    def test_douyin_post_mapping(self):
        raw = {
            "posts": [
                {
                    "aweme_id": "dy001",
                    "desc": "贷款避坑指南",
                    "author": {"nickname": "抖音达人", "uid": "du001"},
                    "stats": {
                        "digg_count": "800",
                        "comment_count": "50",
                        "collect_count": "200",
                    },
                }
            ],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "douyin")
        assert len(posts) == 1
        assert posts[0].post_id == "dy001"
        assert posts[0].like_count == 800
        assert posts[0].is_hot is True

    # Future: bilibili mapper test (platform not yet in MVP, mapper kept for forward compatibility)
    def test_bilibili_post_mapping(self):
        raw = {
            "posts": [
                {
                    "bvid": "BV1test",
                    "title": "B站贷款科普",
                    "desc": "详细讲解",
                    "owner": {"name": "UP主", "mid": "12345"},
                    "stat": {"like": "300", "reply": "40", "favorite": "100"},
                }
            ],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "bilibili")
        assert len(posts) == 1
        assert posts[0].post_id == "BV1test"
        assert posts[0].like_count == 300

    # Future: weibo mapper test (platform not yet in MVP, mapper kept for forward compatibility)
    def test_weibo_post_mapping(self):
        raw = {
            "posts": [
                {
                    "id": "wb001",
                    "text_raw": "微博内容",
                    "user": {"screen_name": "微博用户", "id": "wu001"},
                    "attitudes_count": "100",
                    "comments_count": "20",
                    "reposts_count": "30",
                }
            ],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "weibo")
        assert len(posts) == 1
        assert posts[0].post_id == "wb001"
        assert posts[0].content == "微博内容"

    # Future: kuaishou mapper test (platform not yet in MVP, mapper kept for forward compatibility)
    def test_kuaishou_post_mapping(self):
        raw = {
            "posts": [
                {
                    "id": "ks001",
                    "caption": "快手视频",
                    "author": {"name": "快手用户", "id": "ku001"},
                    "likeCount": "200",
                    "commentCount": "15",
                }
            ],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "kuaishou")
        assert len(posts) == 1
        assert posts[0].post_id == "ks001"

    def test_zhihu_post_mapping(self):
        raw = {
            "posts": [
                {
                    "id": "zh001",
                    "title": "征信花了怎么办？",
                    "excerpt": "知乎回答摘要",
                    "author": {"name": "知乎用户", "id": "zu001"},
                    "voteup_count": "50",
                    "comment_count": "10",
                }
            ],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "zhihu")
        assert len(posts) == 1
        assert posts[0].post_id == "zh001"
        assert posts[0].title == "征信花了怎么办？"

    # Future: tieba mapper test (platform not yet in MVP, mapper kept for forward compatibility)
    def test_tieba_post_mapping(self):
        raw = {
            "posts": [
                {
                    "id": "tb001",
                    "title": "贴吧帖子",
                    "author": {"name": "贴吧用户"},
                    "reply_num": "25",
                }
            ],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "tieba")
        assert len(posts) == 1
        assert posts[0].post_id == "tb001"

    def test_comment_mapping(self):
        raw = {
            "posts": [],
            "comments": [
                {
                    "id": "c001",
                    "note_id": "p001",
                    "content": "求联系方式！",
                    "user_info": {"nickname": "评论者", "user_id": "cu001"},
                    "like_count": "3",
                }
            ],
        }
        _, comments = map_platform_data(raw, "xhs")
        assert len(comments) == 1
        c = comments[0]
        assert c.comment_id == "c001"
        assert c.post_id == "p001"
        assert c.content == "求联系方式！"
        assert c.user_name == "评论者"
        assert c.like_count == 3

    def test_empty_data(self):
        posts, comments = map_platform_data({"posts": [], "comments": []}, "xhs")
        assert posts == []
        assert comments == []

    def test_skip_invalid_posts(self):
        raw = {
            "posts": [{"no_id_field": True}, {"note_id": ""}, "not_a_dict"],
            "comments": [],
        }
        posts, _ = map_platform_data(raw, "xhs")
        assert len(posts) == 0

    def test_parse_datetime_iso(self):
        result = _parse_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024

    def test_parse_datetime_timestamp(self):
        result = _parse_datetime(1705312200)
        assert result is not None

    def test_parse_datetime_none(self):
        assert _parse_datetime(None) is None
        assert _parse_datetime("") is None

    def test_is_hot_threshold(self):
        assert _is_hot(80, 0, 0) is True
        assert _is_hot(0, 20, 0) is True
        assert _is_hot(0, 0, 50) is True
        assert _is_hot(10, 2, 1) is False

    def test_supported_platforms(self):
        assert "xhs" in SUPPORTED_PLATFORMS
        assert "douyin" in SUPPORTED_PLATFORMS
        assert "zhihu" in SUPPORTED_PLATFORMS

    def test_platform_labels(self):
        assert PLATFORM_LABELS["xhs"] == "小红书"
        assert PLATFORM_LABELS["douyin"] == "抖音"
        assert PLATFORM_LABELS["zhihu"] == "知乎"


class TestMediaCrawlerBridge:
    def test_health_check_unreachable(self):
        bridge = MediaCrawlerBridge(api_base_url="http://127.0.0.1:99999")
        assert bridge.health_check() is False

    def test_parse_note_ids_from_urls(self):
        bridge = MediaCrawlerBridge()
        result = bridge._parse_ids(
            "https://www.xiaohongshu.com/explore/abc123, https://www.xiaohongshu.com/explore/def456"
        )
        assert result == "abc123,def456"

    def test_parse_note_ids_from_ids(self):
        bridge = MediaCrawlerBridge()
        result = bridge._parse_ids("abc123, def456")
        assert result == "abc123,def456"

    def test_parse_note_ids_empty(self):
        bridge = MediaCrawlerBridge()
        assert bridge._parse_ids("") == ""

    def test_default_api_base(self):
        bridge = MediaCrawlerBridge()
        assert bridge.api_base_url == "http://127.0.0.1:8080"

    def test_custom_api_base(self):
        bridge = MediaCrawlerBridge(api_base_url="http://mc:9090")
        assert bridge.api_base_url == "http://mc:9090"

    def test_create_crawl_task_uses_new_raw_task_api(self, monkeypatch):
        calls = {}

        def fake_post(url, json, timeout):
            calls["url"] = url
            calls["json"] = json
            return httpx.Response(200, json={"id": 7, "status": "running"})

        monkeypatch.setattr(httpx, "post", fake_post)
        bridge = MediaCrawlerBridge(api_base_url="http://mc:9090")

        task = bridge.create_crawl_task(
            platform="douyin",
            source_type="keyword",
            source_value="信用贷",
            login_type="cookie",
            max_posts=20,
            enable_comments=True,
            cookies="a=b",
        )

        assert task["id"] == 7
        assert calls["url"] == "http://mc:9090/api/crawl-tasks"
        assert calls["json"]["platform"] == "dy"
        assert calls["json"]["source_type"] == "keyword"
        assert calls["json"]["source_value"] == "信用贷"

    def test_fetch_raw_task_result_uses_raw_posts_and_comments_api(self, monkeypatch):
        responses = {
            "http://mc:9090/api/crawl-tasks/7": {"id": 7, "status": "success"},
            "http://mc:9090/api/crawl-tasks/7/raw-posts": {
                "items": [
                    {
                        "raw_id": "p1",
                        "content_text": "标题\n正文",
                        "author_name": "作者",
                        "raw_data": {"note_id": "p1", "title": "标题", "desc": "正文"},
                    }
                ],
                "total": 1,
            },
            "http://mc:9090/api/crawl-tasks/7/raw-comments": {
                "items": [
                    {
                        "raw_id": "c1",
                        "post_raw_id": "p1",
                        "content_text": "想咨询",
                        "author_name": "用户",
                        "raw_data": {"comment_id": "c1", "note_id": "p1", "content": "想咨询"},
                    }
                ],
                "total": 1,
            },
        }

        def fake_get(url, params=None, timeout=None):
            return httpx.Response(200, json=responses[url])

        monkeypatch.setattr(httpx, "get", fake_get)
        bridge = MediaCrawlerBridge(api_base_url="http://mc:9090")

        raw = bridge.wait_for_task_result(task_id=7, platform="xhs")

        assert raw["platform"] == "xhs"
        assert raw["posts"][0]["note_id"] == "p1"
        assert raw["comments"][0]["comment_id"] == "c1"


class TestMediaCrawlerCollector:
    def test_unsupported_platform_raises(self):
        collector = MediaCrawlerCollector()
        source = SimpleNamespace(
            source_type="keyword",
            platform="unsupported",
            value="test",
            config={},
        )
        with pytest.raises(ValueError, match="不支持平台"):
            collector.collect(source)

    def test_empty_value_raises(self):
        collector = MediaCrawlerCollector()
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            value="",
            config={},
        )
        with pytest.raises(ValueError, match="不能为空"):
            collector.collect(source)

    @patch.object(MediaCrawlerBridge, "wait_for_task_result")
    @patch.object(MediaCrawlerBridge, "create_crawl_task")
    @patch.object(MediaCrawlerBridge, "health_check")
    def test_collect_keyword_search(self, mock_health, mock_create, mock_wait):
        mock_health.return_value = True
        mock_create.return_value = {"id": 7, "status": "running"}
        mock_wait.return_value = {
            "platform": "xhs",
            "posts": [
                {
                    "note_id": "n001",
                    "title": "Test",
                    "desc": "Content",
                    "user": {"nickname": "User", "user_id": "u1"},
                    "interact_info": {"liked_count": "10"},
                }
            ],
            "comments": [],
        }

        collector = MediaCrawlerCollector()
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            value="征信修复",
            config={"collector_type": "media_crawler", "login_type": "cookie", "cookies": "test=1"},
        )
        result = collector.collect(source)
        assert len(result.posts) == 1
        assert result.posts[0].post_id == "n001"
        assert result.metadata["source"] == "media_crawler"
        assert result.metadata["platform"] == "xhs"
        assert result.metadata["crawl_type"] == "search"

    @patch.object(MediaCrawlerBridge, "wait_for_task_result")
    @patch.object(MediaCrawlerBridge, "create_crawl_task")
    @patch.object(MediaCrawlerBridge, "health_check")
    def test_collect_competitor_account(self, mock_health, mock_create, mock_wait):
        mock_health.return_value = True
        mock_create.return_value = {"id": 8, "status": "running"}
        mock_wait.return_value = {
            "platform": "douyin",
            "posts": [
                {
                    "aweme_id": "dy001",
                    "desc": "Video",
                    "author": {"nickname": "Creator", "uid": "du1"},
                    "stats": {"digg_count": "50"},
                }
            ],
            "comments": [],
        }

        collector = MediaCrawlerCollector()
        source = SimpleNamespace(
            source_type="competitor_account",
            platform="douyin",
            value="https://www.douyin.com/user/xxx",
            config={"collector_type": "media_crawler", "login_type": "cookie", "cookies": "test=1"},
        )
        result = collector.collect(source)
        assert len(result.posts) == 1
        assert result.metadata["crawl_type"] == "creator"


class TestCollectorFactoryMediaCrawler:
    def test_media_crawler_in_supported_collectors(self):
        collectors = CollectorFactory.get_supported_collectors()
        assert list(collectors.keys()) == ["media_crawler"]
        assert collectors["media_crawler"]["status"] == "ready"
        assert "keyword" in collectors["media_crawler"]["supports"]

    def test_factory_creates_media_crawler(self):
        source = SimpleNamespace(
            source_type="keyword",
            platform="xhs",
            value="test",
            config={"collector_type": "media_crawler", "login_type": "cookie", "cookies": "test=1"},
        )
        collector = CollectorFactory.create(source)
        assert isinstance(collector, MediaCrawlerCollector)

    def test_config_validates_media_crawler(self):
        config = CollectorConfig(collector_type="media_crawler", login_type="cookie")
        is_valid, _ = config.validate_collector_type()
        assert is_valid is True

        is_valid2, _ = config.validate_for_collector_type()
        assert is_valid2 is True

    def test_config_rejects_invalid_login_type(self):
        config = CollectorConfig(collector_type="media_crawler", login_type="invalid")
        is_valid, msg = config.validate_for_collector_type()
        assert is_valid is False
        assert "login_type" in msg

    def test_no_more_douyin_zhihu_stubs(self):
        collectors = CollectorFactory.get_supported_collectors()
        assert "douyin" not in collectors
        assert "zhihu" not in collectors
