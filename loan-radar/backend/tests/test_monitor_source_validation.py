import pytest

from app.schemas.monitor_source import MonitorSourceCreate
from app.services.monitor_source_service import validate_monitor_source_payload


def test_manual_post_playwright_requires_http_url():
    payload = MonitorSourceCreate(
        source_type="manual_post",
        platform="xhs",
        name="指定帖子",
        value="not-a-url",
        config={"collector_type": "playwright"},
        enabled=True,
    )

    with pytest.raises(ValueError, match="manual_post playwright source.value must be a valid http/https URL"):
        validate_monitor_source_payload(payload)


def test_keyword_playwright_is_rejected():
    payload = MonitorSourceCreate(
        source_type="keyword",
        platform="xhs",
        name="关键词",
        value="征信花了",
        config={"collector_type": "playwright"},
        enabled=True,
    )

    with pytest.raises(ValueError, match="playwright collector only supports manual_post"):
        validate_monitor_source_payload(payload)

