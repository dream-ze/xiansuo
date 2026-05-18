import pytest

from app.schemas.monitor_source import MonitorSourceCreate
from app.services.monitor_source_service import validate_monitor_source_payload, validate_platform
from app.services.collection_task_service import create_collection_task


def test_keyword_media_crawler_is_allowed():
    payload = MonitorSourceCreate(
        source_type="keyword",
        platform="xhs",
        name="关键词",
        value="征信花了",
        config={"collector_type": "media_crawler", "login_type": "qrcode"},
        enabled=True,
    )

    validate_monitor_source_payload(payload)


def test_competitor_account_media_crawler_is_allowed():
    payload = MonitorSourceCreate(
        source_type="competitor_account",
        platform="douyin",
        name="同行账号",
        value="https://www.douyin.com/user/xxx",
        config={"collector_type": "media_crawler", "login_type": "qrcode"},
        enabled=True,
    )

    validate_monitor_source_payload(payload)


def test_manual_post_media_crawler_is_allowed():
    payload = MonitorSourceCreate(
        source_type="manual_post",
        platform="xhs",
        name="指定帖子",
        value="https://www.xiaohongshu.com/explore/abc",
        config={"collector_type": "media_crawler", "login_type": "qrcode"},
        enabled=True,
    )

    validate_monitor_source_payload(payload)


def test_zhihu_media_crawler_is_allowed():
    payload = MonitorSourceCreate(
        source_type="keyword",
        platform="zhihu",
        name="知乎关键词",
        value="贷款",
        config={"collector_type": "media_crawler", "login_type": "qrcode"},
        enabled=True,
    )

    validate_monitor_source_payload(payload)


def test_xhs_collector_type_is_rejected():
    payload = MonitorSourceCreate(
        source_type="keyword",
        platform="xhs",
        name="关键词",
        value="征信花了",
        config={"collector_type": "xhs"},
        enabled=True,
    )

    with pytest.raises(ValueError, match="[Uu]nsupported"):
        validate_monitor_source_payload(payload)


@pytest.mark.parametrize("platform", ["kuaishou", "bilibili", "weibo", "tieba", "other"])
def test_unsupported_platform_is_rejected(platform):
    with pytest.raises(ValueError, match="当前 MVP 仅支持 xhs/douyin/zhihu"):
        validate_platform(platform)


@pytest.mark.parametrize("platform", ["kuaishou", "bilibili", "weibo", "tieba", "other"])
def test_unsupported_platform_monitor_source_is_rejected(platform):
    payload = MonitorSourceCreate(
        source_type="keyword",
        platform=platform,
        name="不支持的平台",
        value="测试",
        config={"collector_type": "media_crawler", "login_type": "qrcode"},
        enabled=True,
    )

    with pytest.raises(ValueError, match="当前 MVP 仅支持 xhs/douyin/zhihu"):
        validate_monitor_source_payload(payload)


@pytest.mark.parametrize("platform", ["xhs", "douyin", "zhihu"])
def test_supported_platform_passes_validation(platform):
    validate_platform(platform)
