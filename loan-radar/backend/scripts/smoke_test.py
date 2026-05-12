#!/usr/bin/env python3
import json
import os
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class SmokeTestError(Exception):
    pass


@dataclass
class StepResult:
    step_no: int
    title: str
    detail: str = ""


class ApiClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        status_code, headers, body = self.request_raw(
            method=method,
            path=path,
            params=params,
            payload=payload,
        )
        content_type = ""
        for header_name, header_value in headers.items():
            if header_name.lower() == "content-type":
                content_type = header_value
                break

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SmokeTestError(f"{method} {path} returned invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise SmokeTestError(f"{method} {path} returned non-object JSON")

        if data.get("success") is not True:
            raise SmokeTestError(
                f"{method} {path} returned success=false, message={data.get('message')}"
            )
        return data

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"

        body_bytes = None
        headers = {}
        if payload is not None:
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url=url, data=body_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                raw = resp.read()
                return resp.status, dict(resp.headers.items()), raw
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise SmokeTestError(
                f"{method} {path} failed with HTTP {exc.code}, body={err_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SmokeTestError(
                f"{method} {path} network error: {exc.reason}"
            ) from exc


class SmokeRunner:
    def __init__(self) -> None:
        self.base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.manual_post_url = os.getenv("TEST_MANUAL_POST_URL", "https://example.com/test-manual-post")
        self.timeout_seconds = int(os.getenv("SMOKE_TIMEOUT_SECONDS", "30"))
        self.min_lead_level_classes = int(os.getenv("MIN_LEAD_LEVEL_CLASSES", "2"))
        self.client = ApiClient(self.base_url, timeout_seconds=self.timeout_seconds)
        self.results: list[StepResult] = []

        self.keyword_source_id: int | None = None
        self.mock_task: dict[str, Any] | None = None
        self.manual_source_id: int | None = None
        self.playwright_task: dict[str, Any] | None = None

    def _check_openapi_endpoint_exists(self, path: str, method: str) -> bool:
        try:
            status, _, body = self.client.request_raw("GET", "/openapi.json")
            if status != 200:
                return False
            payload = json.loads(body.decode("utf-8"))
            paths = payload.get("paths")
            if not isinstance(paths, dict):
                return False
            path_item = paths.get(path)
            if not isinstance(path_item, dict):
                return False
            return method.lower() in path_item
        except Exception:
            return False

    def _raise_missing_endpoint_hint(self, raw_path: str, templated_path: str, method: str) -> None:
        exists = self._check_openapi_endpoint_exists(templated_path, method)
        if not exists:
            raise SmokeTestError(
                f"{method.upper()} {raw_path} returned 404 and endpoint is missing in /openapi.json. "
                "Current backend process may be stale and has not loaded latest routes. "
                "Please restart backend service and rerun smoke test."
            )

    def run(self) -> None:
        self._run_step(0, "健康检查", self._health_check)
        self._run_step(1, "创建 keyword 监控源", self._step_1_create_keyword_source)
        self._run_step(2, "触发 mock 采集", self._step_2_trigger_mock_crawl)
        self._run_step(3, "检查 crawl_task 成功", self._step_3_verify_mock_task_success)
        self._run_step(4, "检查 posts 有数据", self._step_4_verify_keyword_posts)
        self._run_step(5, "检查 comments 有数据", self._step_5_verify_keyword_comments)
        self._run_step(6, "检查 leads 有数据并覆盖多类等级", self._step_6_verify_keyword_leads)
        self._run_step(7, "调用 leads/export 并检查 CSV", self._step_7_export_leads_csv)
        self._run_step(8, "调用 daily-reports/generate", self._step_8_generate_daily_report)
        self._run_step(9, "调用 daily-reports/today", self._step_9_get_today_report)
        self._run_step(10, "创建 manual_post 监控源", self._step_10_create_manual_post_source)
        self._run_step(11, "触发 Playwright 采集", self._step_11_trigger_playwright_crawl)

        task_status = (self.playwright_task or {}).get("status")
        if task_status == "success":
            self._run_step(
                12,
                "Playwright 成功分支：检查 posts/comments/leads",
                self._step_12_verify_playwright_success_branch,
            )
        elif task_status == "failed":
            self._run_step(
                13,
                "Playwright 失败分支：检查 failed/error_message/服务健康",
                self._step_13_verify_playwright_failed_branch,
            )
        else:
            raise SmokeTestError(f"Step 11 returned unexpected crawl_task.status={task_status}")

        print("\nPASS")

    def _run_step(self, step_no: int, title: str, fn) -> None:
        print(f"\n[STEP {step_no}] {title}")
        try:
            detail = fn()
            detail_text = "" if detail is None else str(detail)
            self.results.append(StepResult(step_no=step_no, title=title, detail=detail_text))
            if detail_text:
                print(f"[OK] {detail_text}")
            else:
                print("[OK]")
        except Exception as exc:
            print(f"[FAIL] {exc}")
            raise SmokeTestError(f"Step {step_no} failed: {title}. reason={exc}") from exc

    def _health_check(self) -> str:
        status, _, body = self.client.request_raw("GET", "/health")
        if status != 200:
            raise SmokeTestError(f"/health status={status}")
        data = json.loads(body.decode("utf-8"))
        if data.get("status") != "ok":
            raise SmokeTestError(f"/health payload invalid: {data}")
        return f"base_url={self.base_url}"

    def _step_1_create_keyword_source(self) -> str:
        payload = {
            "source_type": "keyword",
            "platform": "xhs",
            "name": "征信花了",
            "value": "征信花了",
            "config": {"collector_type": "mock"},
            "enabled": True,
        }
        response = self.client.request_json("POST", "/api/monitor-sources", payload=payload)
        data = response.get("data") or {}
        source_id = data.get("id")
        if not isinstance(source_id, int):
            raise SmokeTestError(f"create keyword source missing id, data={data}")
        self.keyword_source_id = source_id
        return f"source_id={source_id}"

    def _step_2_trigger_mock_crawl(self) -> str:
        if self.keyword_source_id is None:
            raise SmokeTestError("keyword_source_id is None")
        crawl_path = f"/api/monitor-sources/{self.keyword_source_id}/crawl"
        try:
            response = self.client.request_json(
                "POST",
                crawl_path,
            )
        except SmokeTestError as exc:
            message = str(exc)
            if "failed with HTTP 404" in message and '"detail":"Not Found"' in message:
                self._raise_missing_endpoint_hint(
                    raw_path=crawl_path,
                    templated_path="/api/monitor-sources/{monitor_source_id}/crawl",
                    method="post",
                )
            raise
        data = response.get("data") or {}
        if not isinstance(data.get("id"), int):
            raise SmokeTestError(f"trigger mock crawl missing task id, data={data}")
        self.mock_task = data
        return f"crawl_task_id={data['id']}, status={data.get('status')}"

    def _step_3_verify_mock_task_success(self) -> str:
        task = self.mock_task or {}
        status = task.get("status")
        if status != "success":
            raise SmokeTestError(f"mock crawl task status is {status}, expected success")
        return (
            f"task_id={task.get('id')}, post_count={task.get('post_count')}, "
            f"comment_count={task.get('comment_count')}, lead_count={task.get('lead_count')}"
        )

    def _step_4_verify_keyword_posts(self) -> str:
        if self.keyword_source_id is None:
            raise SmokeTestError("keyword_source_id is None")

        response = self.client.request_json(
            "GET",
            "/api/posts",
            params={
                "source_id": self.keyword_source_id,
                "source_type": "keyword",
                "page": 1,
                "page_size": 100,
            },
        )
        page = response.get("data") or {}
        items = page.get("items") or []
        if not items:
            raise SmokeTestError("posts items is empty for keyword source")
        return f"posts={len(items)}, total={page.get('total')}"

    def _step_5_verify_keyword_comments(self) -> str:
        if self.keyword_source_id is None:
            raise SmokeTestError("keyword_source_id is None")

        posts_resp = self.client.request_json(
            "GET",
            "/api/posts",
            params={
                "source_id": self.keyword_source_id,
                "source_type": "keyword",
                "page": 1,
                "page_size": 100,
            },
        )
        posts = (posts_resp.get("data") or {}).get("items") or []
        post_ids = [post.get("post_id") for post in posts if post.get("post_id")]
        if not post_ids:
            raise SmokeTestError("keyword posts missing post_id")

        total_comments = 0
        checked_posts = 0
        for post_id in post_ids[:5]:
            comments_resp = self.client.request_json(
                "GET",
                "/api/comments",
                params={"post_id": post_id, "page": 1, "page_size": 100},
            )
            page = comments_resp.get("data") or {}
            total_comments += int(page.get("total") or 0)
            checked_posts += 1

        if total_comments <= 0:
            raise SmokeTestError("comments total is 0 for keyword posts")
        return f"checked_posts={checked_posts}, comments_total={total_comments}"

    def _step_6_verify_keyword_leads(self) -> str:
        if self.keyword_source_id is None:
            raise SmokeTestError("keyword_source_id is None")

        response = self.client.request_json(
            "GET",
            "/api/leads",
            params={"source_type": "keyword", "page": 1, "page_size": 100},
        )
        page = response.get("data") or {}
        items = page.get("items") or []

        source_leads = [item for item in items if item.get("source_id") == self.keyword_source_id]
        if not source_leads:
            raise SmokeTestError("leads items is empty for keyword source")

        valid_levels = {"A", "B", "C", "D"}
        levels = {item.get("lead_level") for item in source_leads if item.get("lead_level") in valid_levels}
        if len(levels) < self.min_lead_level_classes:
            raise SmokeTestError(
                "lead levels coverage is insufficient: "
                f"got={sorted(levels)}, required_classes>={self.min_lead_level_classes}"
            )

        return f"leads={len(source_leads)}, lead_levels={sorted(levels)}"

    def _step_7_export_leads_csv(self) -> str:
        status, headers, body = self.client.request_raw(
            "GET",
            "/api/leads/export",
            params={"source_type": "keyword"},
        )
        if status != 200:
            raise SmokeTestError(f"leads/export status={status}")

        content_type = ""
        for header_name, header_value in headers.items():
            if header_name.lower() == "content-type":
                content_type = header_value
                break

        if not body:
            raise SmokeTestError("leads/export returned empty body")

        decoded = body.decode("utf-8-sig", errors="replace")
        if "线索等级" not in decoded:
            raise SmokeTestError("leads/export csv header missing expected column '线索等级'")

        return f"csv_bytes={len(body)}"

    def _step_8_generate_daily_report(self) -> str:
        response = self.client.request_json("POST", "/api/daily-reports/generate")
        data = response.get("data") or {}
        if data.get("report_date") is None:
            raise SmokeTestError(f"generate daily report missing report_date, data={data}")
        return f"report_date={data.get('report_date')}, lead_count={data.get('lead_count')}"

    def _step_9_get_today_report(self) -> str:
        response = self.client.request_json("GET", "/api/daily-reports/today")
        data = response.get("data") or {}
        if data.get("id") is None:
            raise SmokeTestError(f"today report missing id, data={data}")
        return f"report_id={data.get('id')}, report_date={data.get('report_date')}"

    def _step_10_create_manual_post_source(self) -> str:
        payload = {
            "source_type": "manual_post",
            "platform": "xhs",
            "name": "manual_post_smoke_test",
            "value": self.manual_post_url,
            "config": {"collector_type": "playwright"},
            "enabled": True,
        }
        response = self.client.request_json("POST", "/api/monitor-sources", payload=payload)
        data = response.get("data") or {}
        source_id = data.get("id")
        if not isinstance(source_id, int):
            raise SmokeTestError(f"create manual_post source missing id, data={data}")
        self.manual_source_id = source_id
        return f"source_id={source_id}, value={self.manual_post_url}"

    def _step_11_trigger_playwright_crawl(self) -> str:
        if self.manual_source_id is None:
            raise SmokeTestError("manual_source_id is None")
        crawl_path = f"/api/monitor-sources/{self.manual_source_id}/crawl"
        try:
            response = self.client.request_json(
                "POST",
                crawl_path,
            )
        except SmokeTestError as exc:
            message = str(exc)
            if "failed with HTTP 404" in message and '"detail":"Not Found"' in message:
                self._raise_missing_endpoint_hint(
                    raw_path=crawl_path,
                    templated_path="/api/monitor-sources/{monitor_source_id}/crawl",
                    method="post",
                )
            raise
        data = response.get("data") or {}
        if not isinstance(data.get("id"), int):
            raise SmokeTestError(f"trigger playwright crawl missing task id, data={data}")

        self.playwright_task = data
        return (
            f"crawl_task_id={data.get('id')}, status={data.get('status')}, "
            f"error_message={data.get('error_message')}"
        )

    def _step_12_verify_playwright_success_branch(self) -> str:
        if self.manual_source_id is None:
            raise SmokeTestError("manual_source_id is None")

        posts_resp = self.client.request_json(
            "GET",
            "/api/posts",
            params={
                "source_id": self.manual_source_id,
                "source_type": "manual_post",
                "page": 1,
                "page_size": 100,
            },
        )
        posts_page = posts_resp.get("data") or {}
        posts = posts_page.get("items") or []
        if not posts:
            raise SmokeTestError("manual_post posts is empty on success branch")

        post_ids = [post.get("post_id") for post in posts if post.get("post_id")]
        if not post_ids:
            raise SmokeTestError("manual_post posts missing post_id on success branch")

        comments_total = 0
        for post_id in post_ids[:5]:
            comments_resp = self.client.request_json(
                "GET",
                "/api/comments",
                params={"post_id": post_id, "page": 1, "page_size": 100},
            )
            comments_total += int((comments_resp.get("data") or {}).get("total") or 0)
        if comments_total <= 0:
            raise SmokeTestError("manual_post comments total is 0 on success branch")

        leads_resp = self.client.request_json(
            "GET",
            "/api/leads",
            params={"source_type": "manual_post", "page": 1, "page_size": 100},
        )
        lead_items = (leads_resp.get("data") or {}).get("items") or []
        manual_leads = [item for item in lead_items if item.get("source_id") == self.manual_source_id]
        if not manual_leads:
            raise SmokeTestError("manual_post leads is empty on success branch")

        return (
            f"posts={len(posts)}, comments_total={comments_total}, "
            f"leads={len(manual_leads)}"
        )

    def _step_13_verify_playwright_failed_branch(self) -> str:
        task = self.playwright_task or {}
        status = task.get("status")
        error_message = task.get("error_message")

        if status != "failed":
            raise SmokeTestError(f"playwright task status={status}, expected failed")
        if not error_message or not str(error_message).strip():
            raise SmokeTestError("playwright task error_message is empty")

        # 失败后确认服务仍存活，避免因采集异常导致后端崩溃
        status_code, _, body = self.client.request_raw("GET", "/health")
        if status_code != 200:
            raise SmokeTestError(f"backend health check failed after playwright error: {status_code}")
        payload = json.loads(body.decode("utf-8"))
        if payload.get("status") != "ok":
            raise SmokeTestError(f"backend health payload invalid after playwright error: {payload}")

        return f"task_id={task.get('id')}, error_message={error_message}"


def main() -> int:
    start_at = datetime.now()
    print("Loan Radar Backend Smoke Test")
    print(f"Start time: {start_at.isoformat(sep=' ', timespec='seconds')}")

    runner = SmokeRunner()
    try:
        runner.run()
        return 0
    except Exception as exc:
        print("\nFAIL")
        print(str(exc))
        print("\nTraceback:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
