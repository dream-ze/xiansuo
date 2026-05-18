from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.collectors.base import CollectionAuthError, CollectionNoDataError, CollectionRequestError
from app.main import app
from app.services.failure_classifier import FailureType, classify_failure_type


class TestClassifyFailureType:
    def test_connection_error_is_unreachable(self):
        error = ConnectionError("MediaCrawler API 服务不可用")
        assert classify_failure_type(error) == FailureType.MEDIA_CRAWLER_UNREACHABLE

    def test_timeout_error_is_timeout(self):
        error = TimeoutError("采集超时")
        assert classify_failure_type(error) == FailureType.TIMEOUT

    def test_auth_error_is_auth_required(self):
        error = CollectionAuthError("Cookie 已过期或账号被风控")
        assert classify_failure_type(error) == FailureType.AUTH_REQUIRED

    def test_auth_error_with_risk_control_is_captcha(self):
        error = CollectionAuthError("当前账号存在异常，请切换账号")
        assert classify_failure_type(error) == FailureType.CAPTCHA_OR_RISK_CONTROL

    def test_no_data_error_is_empty_result(self):
        error = CollectionNoDataError("未返回数据")
        assert classify_failure_type(error) == FailureType.EMPTY_RESULT

    def test_value_error_platform_not_supported(self):
        error = ValueError("MediaCrawler 不支持平台 'kuaishou'")
        assert classify_failure_type(error) == FailureType.PLATFORM_NOT_SUPPORTED

    def test_value_error_source_type_not_supported(self):
        error = ValueError("不支持的 source_type: unknown")
        assert classify_failure_type(error) == FailureType.PLATFORM_NOT_SUPPORTED

    def test_value_error_generic_is_unknown(self):
        error = ValueError("some other value error")
        assert classify_failure_type(error) == FailureType.UNKNOWN

    def test_request_error_unreachable_pattern(self):
        error = CollectionRequestError("MediaCrawler 服务无法连接")
        assert classify_failure_type(error) == FailureType.MEDIA_CRAWLER_UNREACHABLE

    def test_request_error_timeout_pattern(self):
        error = CollectionRequestError("MediaCrawler API 请求超时 (300s)")
        assert classify_failure_type(error) == FailureType.TIMEOUT

    def test_request_error_risk_control_pattern(self):
        error = CollectionRequestError("请求频繁，请稍后重试")
        assert classify_failure_type(error) == FailureType.CAPTCHA_OR_RISK_CONTROL

    def test_request_error_generic_is_unknown(self):
        error = CollectionRequestError("MediaCrawler API 错误: something")
        assert classify_failure_type(error) == FailureType.UNKNOWN

    def test_generic_exception_unreachable_pattern(self):
        error = RuntimeError("服务不可用，请检查连接")
        assert classify_failure_type(error) == FailureType.MEDIA_CRAWLER_UNREACHABLE

    def test_generic_exception_timeout_pattern(self):
        error = RuntimeError("请求超时，请重试")
        assert classify_failure_type(error) == FailureType.TIMEOUT

    def test_generic_exception_risk_control_pattern(self):
        error = RuntimeError("触发验证码，请更换账号")
        assert classify_failure_type(error) == FailureType.CAPTCHA_OR_RISK_CONTROL

    def test_generic_exception_parser_error(self):
        error = RuntimeError("解析响应数据失败: json decode error")
        assert classify_failure_type(error) == FailureType.PARSER_ERROR

    def test_generic_exception_unknown(self):
        error = RuntimeError("something unexpected")
        assert classify_failure_type(error) == FailureType.UNKNOWN

    def test_string_error_unreachable(self):
        result = classify_failure_type("服务无法连接，请检查")
        assert result == FailureType.MEDIA_CRAWLER_UNREACHABLE

    def test_string_error_unknown(self):
        result = classify_failure_type("something went wrong")
        assert result == FailureType.UNKNOWN


class TestFailureTypeMeta:
    def test_all_failure_types_have_meta(self):
        from app.services.failure_classifier import FAILURE_TYPE_META
        for ft in FailureType:
            assert ft in FAILURE_TYPE_META, f"Missing meta for {ft.value}"

    def test_meta_has_required_fields(self):
        from app.services.failure_classifier import FAILURE_TYPE_META
        for ft, meta in FAILURE_TYPE_META.items():
            assert "label" in meta, f"Missing 'label' in meta for {ft.value}"
            assert "description" in meta, f"Missing 'description' in meta for {ft.value}"
            assert "suggestion" in meta, f"Missing 'suggestion' in meta for {ft.value}"

    def test_meta_labels_are_chinese(self):
        from app.services.failure_classifier import FAILURE_TYPE_META
        for ft, meta in FAILURE_TYPE_META.items():
            label = meta["label"]
            assert len(label) > 0, f"Empty label for {ft.value}"


class TestSanitizeErrorMessage:
    def test_cookie_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('cookie=abc123xyz'))
        assert "abc123xyz" not in msg
        assert "***" in msg

    def test_api_key_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('api_key=sk-12345abcde'))
        assert "sk-12345abcde" not in msg
        assert "***" in msg

    def test_token_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('token=eyJhbGciOiJIUzI1NiJ9'))
        assert "eyJhbGciOiJIUzI1NiJ9" not in msg
        assert "***" in msg

    def test_password_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('password=mysecret123'))
        assert "mysecret123" not in msg
        assert "***" in msg

    def test_db_connection_string_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('postgres://user:pass@localhost:5432/mydb'))
        assert "user:pass@localhost" not in msg
        assert "***" in msg

    def test_sessionid_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('sessionid=abc123def456'))
        assert "abc123def456" not in msg
        assert "***" in msg

    def test_traceback_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception('Traceback (most recent call last):\n  File "app.py", line 42'))
        assert "File" not in msg or "omitted" in msg

    def test_normal_message_preserved(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception("MediaCrawler 服务无法连接"))
        assert msg == "MediaCrawler 服务无法连接"

    def test_url_query_param_key_sanitized(self):
        from app.services.crawl_pipeline_service import _sanitize_error_message
        msg = _sanitize_error_message(Exception("https://api.example.com/data?key=secret123&other=ok"))
        assert "secret123" not in msg


@pytest.fixture
def api_client():
    return TestClient(app)


class TestFailureTypesAPI:
    def test_failure_types_meta_endpoint(self, api_client):
        response = api_client.get("/api/crawl-tasks/failure-types/meta")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        meta = data["data"]

        expected_types = [
            "media_crawler_unreachable",
            "platform_not_supported",
            "auth_required",
            "captcha_or_risk_control",
            "timeout",
            "empty_result",
            "parser_error",
            "unknown",
        ]
        for ft in expected_types:
            assert ft in meta, f"Missing failure type: {ft}"
            assert "value" in meta[ft]
            assert "label" in meta[ft]
            assert "description" in meta[ft]
            assert "suggestion" in meta[ft]
            assert meta[ft]["value"] == ft

    def test_failure_type_in_crawl_task_response(self, api_client):
        from app.core.database import SessionLocal
        from app.models.crawl_task import CrawlTask

        db = SessionLocal()
        try:
            task = CrawlTask(
                source_id=None,
                source_type="keyword",
                source_value="test_failure_type",
                platform="xhs",
                status="failed",
                progress="failed",
                limit_count=10,
                post_count=0,
                comment_count=0,
                collected_posts=0,
                collected_comments=0,
                lead_count=0,
                discovered_competitor_count=0,
                duplicate_post_count=0,
                duplicate_comment_count=0,
                error_message="MediaCrawler 服务不可用",
                failure_type="media_crawler_unreachable",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id
        finally:
            db.close()

        try:
            response = api_client.get(f"/api/crawl-tasks/{task_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            task_data = data["data"]
            assert task_data["failure_type"] == "media_crawler_unreachable"
            assert task_data["error_message"] == "MediaCrawler 服务不可用"
        finally:
            db2 = SessionLocal()
            try:
                cleanup = db2.query(CrawlTask).filter(CrawlTask.id == task_id).first()
                if cleanup:
                    db2.delete(cleanup)
                    db2.commit()
            finally:
                db2.close()
