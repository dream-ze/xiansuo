import pytest

from app.schemas.monitor_source import MonitorSourceCreate
from app.services.monitor_source_service import validate_monitor_source_payload


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
