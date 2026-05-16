#!/usr/bin/env python3
"""MediaCrawler Smoke Test for Loan Radar MVP.

Validates the full pipeline:
  /health -> media-crawler/health -> create source -> trigger crawl ->
  check task -> posts -> comments -> leads -> generate report -> export CSV

Requires:
  - Backend running at SMOKE_BASE_URL (default http://127.0.0.1:8001)
  - MediaCrawler API service running at http://127.0.0.1:8080
  - Database migrated and writable
"""

import csv
import io
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


class SmokeTestError(Exception):
    pass


@dataclass
class StepResult:
    step_no: int
    title: str
    passed: bool = False
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
        params: dict | None = None,
        payload: dict | None = None,
    ) -> dict:
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
                data = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise SmokeTestError(
                f"{method} {path} failed with HTTP {exc.code}, body={err_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SmokeTestError(
                f"{method} {path} network error: {exc.reason}"
            ) from exc

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
        params: dict | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"

        request = urllib.request.Request(url=url, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                raw = resp.read()
                return resp.status, dict(resp.headers.items()), raw
        except urllib.error.HTTPError as exc:
            err_body = exc.read()
            return exc.code, dict(exc.headers.items()), err_body
        except urllib.error.URLError as exc:
            raise SmokeTestError(
                f"{method} {path} network error: {exc.reason}"
            ) from exc


class MediaCrawlerSmokeRunner:
    def __init__(self) -> None:
        self.base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
        self.timeout_seconds = int(os.getenv("SMOKE_TIMEOUT_SECONDS", "30"))
        self.crawl_wait_seconds = int(os.getenv("CRAWL_WAIT_SECONDS", "10"))
        self.client = ApiClient(self.base_url, timeout_seconds=self.timeout_seconds)
        self.results: list[StepResult] = []

        self.source_id: int | None = None
        self.crawl_task_id: int | None = None

    def run(self) -> None:
        self._run_step(1, "检查 /health", self._step_health)
        self._run_step(2, "检查 MediaCrawler 健康状态", self._step_mc_health)
        self._run_step(3, "创建 xhs keyword 监控源（关键词：征信花了）", self._step_create_source)
        self._run_step(4, "触发采集", self._step_trigger_crawl)
        self._run_step(5, "查询采集任务状态", self._step_check_task)
        self._run_step(6, "查询帖子池", self._step_check_posts)
        self._run_step(7, "查询评论池", self._step_check_comments)
        self._run_step(8, "查询线索池", self._step_check_leads)
        self._run_step(9, "生成今日报告", self._step_generate_report)
        self._run_step(10, "导出 CSV", self._step_export_csv)

        self._print_summary()

    def _run_step(self, step_no: int, title: str, fn) -> None:
        print(f"\n[STEP {step_no}] {title}")
        try:
            detail = fn()
            detail_text = "" if detail is None else str(detail)
            self.results.append(StepResult(step_no=step_no, title=title, passed=True, detail=detail_text))
            if detail_text:
                print(f"  [OK] {detail_text}")
            else:
                print("  [OK]")
        except Exception as exc:
            print(f"  [FAIL] {exc}")
            self.results.append(StepResult(step_no=step_no, title=title, passed=False, detail=str(exc)))
            self._print_summary()
            sys.exit(1)

    def _print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("SMOKE TEST SUMMARY")
        print("=" * 60)

        all_passed = True
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            if not r.passed:
                all_passed = False
            line = f"  Step {r.step_no}: [{status}] {r.title}"
            if r.detail:
                line += f" — {r.detail[:80]}"
            print(line)

        print("=" * 60)
        if all_passed:
            print("RESULT: PASS")
        else:
            print("RESULT: FAIL")
            failed = [r for r in self.results if not r.passed]
            for f in failed:
                print(f"  失败原因 (Step {f.step_no}): {f.detail}")

    def _step_health(self) -> str:
        status, _, body = self.client.request_raw("GET", "/health")
        if status != 200:
            raise SmokeTestError(f"/health status={status}")
        data = json.loads(body.decode("utf-8"))
        if data.get("status") != "ok":
            raise SmokeTestError(f"/health payload invalid: {data}")
        return f"base_url={self.base_url}, status=ok"

    def _step_mc_health(self) -> str:
        resp = self.client.request_json("GET", "/api/monitor-sources/media-crawler/health")
        data = resp.get("data") or {}
        mc_status = data.get("status", "unknown")
        api_url = data.get("api_base_url", "")
        platforms = data.get("supported_platforms", [])
        platform_names = [p.get("value", "") for p in platforms] if isinstance(platforms, list) else []
        if mc_status != "healthy":
            raise SmokeTestError(
                f"MediaCrawler status={mc_status}, api_base_url={api_url}. "
                "请确保 MediaCrawler API 服务已启动（默认 http://127.0.0.1:8080）。"
            )
        return f"status={mc_status}, api_url={api_url}, platforms={platform_names}"

    def _step_create_source(self) -> str:
        payload = {
            "source_type": "keyword",
            "platform": "xhs",
            "name": "关键词 - 征信花了",
            "value": "征信花了",
            "config": {
                "collector_type": "media_crawler",
                "login_type": "qrcode",
                "enable_comments": True,
                "max_posts": 10,
                "max_comments_per_post": 10,
            },
            "enabled": True,
        }
        resp = self.client.request_json("POST", "/api/monitor-sources", payload=payload)
        data = resp.get("data") or {}
        source_id = data.get("id")
        if not isinstance(source_id, int):
            raise SmokeTestError(f"create source missing id, data={data}")
        self.source_id = source_id
        return f"source_id={source_id}, name={data.get('name')}"

    def _step_trigger_crawl(self) -> str:
        if self.source_id is None:
            raise SmokeTestError("source_id is None")
        resp = self.client.request_json("POST", f"/api/monitor-sources/{self.source_id}/crawl")
        data = resp.get("data") or {}
        task_id = data.get("id")
        if not isinstance(task_id, int):
            raise SmokeTestError(f"trigger crawl missing task id, data={data}")
        self.crawl_task_id = task_id
        status = data.get("status", "unknown")
        queue_pos = data.get("queue_position")
        return f"crawl_task_id={task_id}, status={status}, queue_position={queue_pos}"

    def _step_check_task(self) -> str:
        if self.crawl_task_id is None:
            raise SmokeTestError("crawl_task_id is None")

        max_wait = self.crawl_wait_seconds
        elapsed = 0
        interval = 2
        while elapsed < max_wait:
            resp = self.client.request_json("GET", f"/api/crawl-tasks/{self.crawl_task_id}")
            data = resp.get("data") or {}
            status = data.get("status", "unknown")
            if status in ("success", "failed"):
                error_msg = data.get("error_message") or ""
                post_count = data.get("post_count", 0)
                comment_count = data.get("comment_count", 0)
                lead_count = data.get("lead_count", 0)
                if status == "failed":
                    raise SmokeTestError(
                        f"crawl task failed: {error_msg}"
                    )
                return (
                    f"status={status}, posts={post_count}, "
                    f"comments={comment_count}, leads={lead_count}"
                )
            time.sleep(interval)
            elapsed += interval

        resp = self.client.request_json("GET", f"/api/crawl-tasks/{self.crawl_task_id}")
        data = resp.get("data") or {}
        status = data.get("status", "unknown")
        if status in ("queued", "running", "pending"):
            return f"status={status} (still processing after {max_wait}s, not a failure)"
        raise SmokeTestError(f"crawl task unexpected status={status}")

    def _step_check_posts(self) -> str:
        resp = self.client.request_json("GET", "/api/posts", params={"page": 1, "page_size": 10})
        data = resp.get("data") or {}
        items = data.get("items") or []
        total = data.get("total", 0)
        return f"posts_total={total}, page_items={len(items)}"

    def _step_check_comments(self) -> str:
        resp = self.client.request_json("GET", "/api/comments", params={"page": 1, "page_size": 10})
        data = resp.get("data") or {}
        items = data.get("items") or []
        total = data.get("total", 0)
        return f"comments_total={total}, page_items={len(items)}"

    def _step_check_leads(self) -> str:
        resp = self.client.request_json("GET", "/api/leads", params={"page": 1, "page_size": 10})
        data = resp.get("data") or {}
        items = data.get("items") or []
        total = data.get("total", 0)
        levels = set()
        for item in items:
            level = item.get("lead_level", "")
            if level:
                levels.add(level)
        return f"leads_total={total}, page_items={len(items)}, levels={sorted(levels)}"

    def _step_generate_report(self) -> str:
        resp = self.client.request_json("POST", "/api/daily-reports/generate")
        data = resp.get("data") or {}
        report_date = data.get("report_date")
        lead_count = data.get("lead_count", 0)
        a_count = data.get("a_lead_count", 0)
        if report_date is None:
            raise SmokeTestError(f"report missing report_date, data={data}")
        return f"report_date={report_date}, leads={lead_count}, A级={a_count}"

    def _step_export_csv(self) -> str:
        status, _, body = self.client.request_raw("GET", "/api/leads/export")
        if status != 200:
            raise SmokeTestError(f"leads/export status={status}")
        if not body:
            raise SmokeTestError("leads/export returned empty body")

        decoded = body.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)
        if not rows:
            raise SmokeTestError("CSV is empty")

        headers = rows[0]
        required = {"线索等级", "来源平台", "状态", "备注"}
        missing = required - set(headers)
        if missing:
            raise SmokeTestError(f"CSV missing columns: {missing}")

        return f"csv_rows={len(rows)}, headers={headers}"


def main() -> int:
    print("Loan Radar MediaCrawler Smoke Test")
    print(f"Base URL: {os.getenv('SMOKE_BASE_URL', 'http://127.0.0.1:8001')}")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    runner = MediaCrawlerSmokeRunner()
    try:
        runner.run()
        return 0
    except Exception as exc:
        print(f"\nUNEXPECTED ERROR: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
