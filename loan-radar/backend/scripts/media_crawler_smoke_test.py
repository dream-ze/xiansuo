#!/usr/bin/env python3
"""Loan Radar 交付验收脚本（Smoke Test）。

支持两种模式：
  - demo 模式（SMOKE_MODE=demo）：MockCollector 演示验收，不依赖 MediaCrawler
  - real 模式（SMOKE_MODE=real）：真实 MediaCrawler 采集验收

验收流程：
  /health -> [real: MediaCrawler 健康检查] -> 创建监控源 -> 触发采集 ->
  查询任务 -> 帖子 -> 评论 -> 线索 -> 日报 -> CSV 导出

环境变量：
  SMOKE_MODE          real / demo（默认 demo）
  SMOKE_BASE_URL      后端地址（默认 http://127.0.0.1:8001）
  SMOKE_TIMEOUT_SECONDS  HTTP 请求超时（默认 30）
  CRAWL_WAIT_SECONDS  等待采集完成秒数（默认 15）
  SMOKE_REPORT_DIR    验收报告输出目录（默认 reports）
"""

from __future__ import annotations

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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SmokeTestError(Exception):
    pass


@dataclass
class StepResult:
    step_no: int
    title: str
    passed: bool = False
    detail: str = ""
    duration_ms: int = 0
    suggestion: str = ""


@dataclass
class SmokeTestReport:
    mode: str
    base_url: str
    started_at: str
    finished_at: str
    result: str
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    steps: list[dict] = field(default_factory=list)
    key_metrics: dict = field(default_factory=dict)
    failure_reason: str = ""
    fix_suggestion: str = ""


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
        headers: dict[str, str] = {}
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


_SUGGESTIONS: dict[str, str] = {
    "health": "请启动后端服务：uvicorn app.main:app --port 8001 --reload",
    "mc_health": "请启动 MediaCrawler API 服务（默认 http://127.0.0.1:8080），或切换为 demo 模式（SMOKE_MODE=demo）",
    "create_source": "请检查后端日志，确认 /api/monitor-sources 接口正常。demo 模式需设置 ENABLE_MOCK_COLLECTOR=true",
    "trigger_crawl": "请检查后端日志，确认采集流水线服务正常。demo 模式需设置 ENABLE_MOCK_COLLECTOR=true",
    "check_task": "采集任务失败，请检查 failure_type 和 error_message。如果是 media_crawler_unreachable，请启动 MediaCrawler 或切换 demo 模式",
    "posts": "帖子池为空，请确认采集任务成功完成。demo 模式下至少应有 5 条帖子",
    "comments": "评论池为空，请确认采集任务成功完成。demo 模式下至少应有评论",
    "leads": "线索池为空，请确认评分服务正常。demo 模式下至少应有线索且覆盖 A/B/C/D 中两个等级",
    "report": "日报生成失败，请检查后端日志确认 daily-reports 服务正常",
    "csv": "CSV 导出失败，请检查 /api/leads/export 接口",
    "lead_levels": "线索等级覆盖不足，请确认评分逻辑是否正常分配 A/B/C/D 等级",
    "csv_data": "CSV 无数据行，请确认线索池中有数据",
}


class SmokeTestRunner:
    def __init__(self) -> None:
        self.mode = os.getenv("SMOKE_MODE", "demo").strip().lower()
        if self.mode not in ("real", "demo"):
            print(f"[WARN] SMOKE_MODE={self.mode!r} 无效，使用默认 demo")
            self.mode = "demo"

        self.base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
        self.timeout_seconds = int(os.getenv("SMOKE_TIMEOUT_SECONDS", "30"))
        self.crawl_wait_seconds = int(os.getenv("CRAWL_WAIT_SECONDS", "15"))
        self.report_dir = os.getenv("SMOKE_REPORT_DIR", "reports").strip()
        self.client = ApiClient(self.base_url, timeout_seconds=self.timeout_seconds)
        self.results: list[StepResult] = []
        self.key_metrics: dict[str, Any] = {}

        self.source_id: int | None = None
        self.crawl_task_id: int | None = None
        self.crawl_task_status: str = ""
        self.crawl_task_failure_type: str | None = None
        self.crawl_task_error_message: str | None = None

        self._step_counter: int = 0

    def run(self) -> bool:
        started_at = datetime.now(timezone.utc).isoformat()
        print(f"\n{'=' * 60}")
        print(f"Loan Radar 交付验收脚本  |  模式: {self.mode.upper()}")
        print(f"Base URL: {self.base_url}")
        print(f"{'=' * 60}\n")

        try:
            self._run_step("健康检查 /health", self._step_health, "health")

            if self.mode == "real":
                self._run_step("MediaCrawler 健康检查", self._step_mc_health, "mc_health")

            self._run_step("创建监控源", self._step_create_source, "create_source")
            self._run_step("触发采集", self._step_trigger_crawl, "trigger_crawl")
            self._run_step("查询采集任务状态", self._step_check_task, "check_task")
            self._run_step("查询帖子池", self._step_check_posts, "posts")
            self._run_step("查询评论池", self._step_check_comments, "comments")
            self._run_step("查询线索池", self._step_check_leads, "leads")
            self._run_step("生成今日报告", self._step_generate_report, "report")
            self._run_step("导出 CSV", self._step_export_csv, "csv")

        except _StopExecution:
            pass

        finished_at = datetime.now(timezone.utc).isoformat()
        all_passed = all(r.passed for r in self.results)
        failed_results = [r for r in self.results if not r.passed]

        report = SmokeTestReport(
            mode=self.mode,
            base_url=self.base_url,
            started_at=started_at,
            finished_at=finished_at,
            result="PASS" if all_passed else "FAIL",
            total_steps=len(self.results),
            passed_steps=sum(1 for r in self.results if r.passed),
            failed_steps=len(failed_results),
            steps=[asdict(r) for r in self.results],
            key_metrics=self.key_metrics,
            failure_reason=failed_results[0].detail if failed_results else "",
            fix_suggestion=failed_results[0].suggestion if failed_results else "",
        )

        self._print_summary(report)
        self._save_report(report)

        return all_passed

    def _run_step(self, title: str, fn, suggestion_key: str) -> None:
        self._step_counter += 1
        step_no = self._step_counter
        print(f"[STEP {step_no}] {title}")

        start = time.monotonic()
        try:
            detail = fn()
            duration_ms = int((time.monotonic() - start) * 1000)
            detail_text = "" if detail is None else str(detail)
            self.results.append(StepResult(
                step_no=step_no,
                title=title,
                passed=True,
                detail=detail_text,
                duration_ms=duration_ms,
            ))
            print(f"  [PASS] {detail_text}  ({duration_ms}ms)")
        except SmokeTestError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            suggestion = _SUGGESTIONS.get(suggestion_key, "")
            self.results.append(StepResult(
                step_no=step_no,
                title=title,
                passed=False,
                detail=str(exc),
                duration_ms=duration_ms,
                suggestion=suggestion,
            ))
            print(f"  [FAIL] {exc}  ({duration_ms}ms)")
            if suggestion:
                print(f"  [修复建议] {suggestion}")
            raise _StopExecution()
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            suggestion = _SUGGESTIONS.get(suggestion_key, "")
            self.results.append(StepResult(
                step_no=step_no,
                title=title,
                passed=False,
                detail=f"Unexpected: {exc}",
                duration_ms=duration_ms,
                suggestion=suggestion,
            ))
            print(f"  [FAIL] Unexpected: {exc}  ({duration_ms}ms)")
            if suggestion:
                print(f"  [修复建议] {suggestion}")
            raise _StopExecution()

    def _print_summary(self, report: SmokeTestReport) -> None:
        print(f"\n{'=' * 60}")
        print(f"验收报告  |  模式: {report.mode.upper()}  |  结果: {report.result}")
        print(f"{'=' * 60}")
        print(f"步骤: {report.passed_steps}/{report.total_steps} 通过")
        print()

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            line = f"  Step {r.step_no}: [{status}] {r.title}"
            if r.detail:
                line += f" — {r.detail[:100]}"
            line += f"  ({r.duration_ms}ms)"
            print(line)
            if not r.passed and r.suggestion:
                print(f"           修复建议: {r.suggestion}")

        print()
        print("关键指标:")
        for k, v in report.key_metrics.items():
            print(f"  {k}: {v}")

        if not all(r.passed for r in self.results):
            print()
            print("失败原因:")
            for r in self.results:
                if not r.passed:
                    print(f"  Step {r.step_no} ({r.title}): {r.detail}")
                    if r.suggestion:
                        print(f"    修复建议: {r.suggestion}")

        print(f"\n{'=' * 60}")
        print(f"最终结果: {report.result}")
        print(f"{'=' * 60}")

    def _save_report(self, report: SmokeTestReport) -> None:
        report_path = Path(self.report_dir) / "smoke_test_result.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n验收报告已保存: {report_path}")

    def _step_health(self) -> str:
        status, _, body = self.client.request_raw("GET", "/health")
        if status != 200:
            raise SmokeTestError(f"/health status={status}")
        data = json.loads(body.decode("utf-8"))
        if data.get("status") != "ok":
            raise SmokeTestError(f"/health payload invalid: {data}")
        self.key_metrics["backend_health"] = "ok"
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
                f"MediaCrawler status={mc_status}, api_base_url={api_url}"
            )
        self.key_metrics["mc_status"] = mc_status
        self.key_metrics["mc_platforms"] = ", ".join(platform_names)
        return f"status={mc_status}, api_url={api_url}, platforms={platform_names}"

    def _step_create_source(self) -> str:
        if self.mode == "demo":
            config = {
                "collector_type": "mock",
                "enable_comments": True,
                "max_posts": 10,
                "max_comments_per_post": 10,
            }
        else:
            config = {
                "collector_type": "media_crawler",
                "login_type": "qrcode",
                "enable_comments": True,
                "max_posts": 10,
                "max_comments_per_post": 10,
            }

        payload = {
            "source_type": "keyword",
            "platform": "xhs",
            "name": "验收测试 - 征信花了",
            "value": "征信花了",
            "config": config,
            "enabled": True,
        }
        resp = self.client.request_json("POST", "/api/monitor-sources", payload=payload)
        data = resp.get("data") or {}
        source_id = data.get("id")
        if not isinstance(source_id, int):
            raise SmokeTestError(f"create source missing id, data={data}")
        self.source_id = source_id
        self.key_metrics["source_id"] = source_id
        return f"source_id={source_id}, collector={config['collector_type']}"

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
        self.key_metrics["crawl_task_id"] = task_id
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
                self.crawl_task_status = status
                self.crawl_task_failure_type = data.get("failure_type")
                self.crawl_task_error_message = data.get("error_message")
                post_count = data.get("post_count", 0)
                comment_count = data.get("comment_count", 0)
                lead_count = data.get("lead_count", 0)
                self.key_metrics["task_status"] = status
                self.key_metrics["task_post_count"] = post_count
                self.key_metrics["task_comment_count"] = comment_count
                self.key_metrics["task_lead_count"] = lead_count
                if self.crawl_task_failure_type:
                    self.key_metrics["failure_type"] = self.crawl_task_failure_type

                if status == "failed":
                    if self.mode == "real":
                        ft = self.crawl_task_failure_type or "unknown"
                        err = self.crawl_task_error_message or ""
                        raise SmokeTestError(
                            f"采集任务失败: failure_type={ft}, error={err}"
                        )
                    else:
                        raise SmokeTestError(
                            f"采集任务失败: {self.crawl_task_error_message}"
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
        self.crawl_task_status = status
        self.key_metrics["task_status"] = status

        if status in ("queued", "running", "pending"):
            if self.mode == "demo":
                raise SmokeTestError(
                    f"demo 模式下采集任务在 {max_wait}s 内未完成，status={status}"
                )
            return f"status={status} (still processing after {max_wait}s, not a failure)"

        raise SmokeTestError(f"crawl task unexpected status={status}")

    def _step_check_posts(self) -> str:
        resp = self.client.request_json("GET", "/api/posts", params={"page": 1, "page_size": 10})
        data = resp.get("data") or {}
        items = data.get("items") or []
        total = data.get("total", 0)
        self.key_metrics["posts_total"] = total

        if self.mode == "demo":
            if total <= 0:
                raise SmokeTestError(
                    f"demo 模式下帖子池应为空，实际 posts_total={total}"
                )
        else:
            if total <= 0 and self.crawl_task_status == "success":
                print("  [WARNING] 采集任务成功但帖子池为空，真实平台可能返回了空结果")

        return f"posts_total={total}, page_items={len(items)}"

    def _step_check_comments(self) -> str:
        resp = self.client.request_json("GET", "/api/comments", params={"page": 1, "page_size": 10})
        data = resp.get("data") or {}
        items = data.get("items") or []
        total = data.get("total", 0)
        self.key_metrics["comments_total"] = total

        if self.mode == "demo":
            if total <= 0:
                raise SmokeTestError(
                    f"demo 模式下评论池不应为空，实际 comments_total={total}"
                )
        else:
            if total <= 0 and self.crawl_task_status == "success":
                print("  [WARNING] 采集任务成功但评论池为空，真实平台可能返回了空结果")

        return f"comments_total={total}, page_items={len(items)}"

    def _step_check_leads(self) -> str:
        resp = self.client.request_json("GET", "/api/leads", params={"page": 1, "page_size": 100})
        data = resp.get("data") or {}
        items = data.get("items") or []
        total = data.get("total", 0)
        self.key_metrics["leads_total"] = total

        valid_levels = {"A", "B", "C", "D"}
        levels = set()
        for item in items:
            level = item.get("lead_level", "")
            if level in valid_levels:
                levels.add(level)
        self.key_metrics["lead_levels"] = ", ".join(sorted(levels))

        if self.mode == "demo":
            if total <= 0:
                raise SmokeTestError(
                    f"demo 模式下线索池不应为空，实际 leads_total={total}"
                )
            if len(levels) < 2:
                raise SmokeTestError(
                    f"demo 模式下线索等级应至少覆盖 A/B/C/D 中的 2 个，"
                    f"实际覆盖: {sorted(levels)}"
                )
        else:
            if total <= 0 and self.crawl_task_status == "success":
                print("  [WARNING] 采集任务成功但线索池为空，评分服务可能未正常工作")

        return f"leads_total={total}, page_items={len(items)}, levels={sorted(levels)}"

    def _step_generate_report(self) -> str:
        resp = self.client.request_json("POST", "/api/daily-reports/generate")
        data = resp.get("data") or {}
        report_date = data.get("report_date")
        lead_count = data.get("lead_count", 0)
        a_count = data.get("a_lead_count", 0)
        if report_date is None:
            raise SmokeTestError(f"report missing report_date, data={data}")
        self.key_metrics["report_date"] = report_date
        self.key_metrics["report_lead_count"] = lead_count
        self.key_metrics["report_a_count"] = a_count

        if self.mode == "demo":
            if lead_count <= 0:
                raise SmokeTestError(
                    f"demo 模式下今日报告应包含线索，实际 lead_count={lead_count}"
                )

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
        data_rows = len(rows) - 1
        self.key_metrics["csv_headers"] = len(headers)
        self.key_metrics["csv_data_rows"] = data_rows

        required = {"线索等级", "来源平台", "状态", "备注"}
        missing = required - set(headers)
        if missing:
            raise SmokeTestError(f"CSV missing columns: {missing}")

        if self.mode == "demo":
            if data_rows < 1:
                raise SmokeTestError(
                    f"demo 模式下 CSV 应至少包含 1 条数据，实际 data_rows={data_rows}"
                )

        return f"csv_rows={len(rows)}, data_rows={data_rows}, headers={headers}"


class _StopExecution(Exception):
    pass


def main() -> int:
    runner = SmokeTestRunner()
    try:
        passed = runner.run()
        return 0 if passed else 1
    except Exception as exc:
        print(f"\nUNEXPECTED ERROR: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
