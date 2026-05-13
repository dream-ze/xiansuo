#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class SmokeError(Exception):
    pass


@dataclass
class TaskSummary:
    task_id: int
    source_type: str
    status: str
    collected_posts: int
    collected_comments: int
    post_count: int
    comment_count: int
    lead_count: int
    error_message: str | None
    discovered_competitor_count: int


class ApiClient:
    def __init__(self, base_url: str, timeout_seconds: int = 60) -> None:
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
        status, raw = self.request_raw(method, path, params=params, payload=payload)
        if status < 200 or status >= 300:
            raise SmokeError(f"{method} {path} returned HTTP {status}")
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise SmokeError(f"{method} {path} returned invalid JSON") from error

        if not isinstance(data, dict):
            raise SmokeError(f"{method} {path} returned non-object JSON")
        return data

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, bytes]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"

        body = None
        headers: dict[str, str] = {}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url=url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise SmokeError(f"{method} {path} failed with HTTP {error.code}, body={detail}") from error
        except urllib.error.URLError as error:
            raise SmokeError(
                f"无法连接后端 {self.base_url}，请先启动服务: uvicorn app.main:app --reload"
            ) from error


class RealCollectionSmoke:
    def __init__(self) -> None:
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.keyword = os.getenv("XHS_TEST_KEYWORD", "征信花了")
        self.post_url = os.getenv("XHS_TEST_POST_URL", "").strip()
        self.driver = (os.getenv("XHS_PROVIDER_DRIVER") or "pc").strip().lower()
        self.spider_path = (os.getenv("XHS_SPIDER_PATH") or "").strip()
        self.client = ApiClient(self.base_url)

    def run(self) -> None:
        if self.driver in {"pc", "spider"} and not os.getenv("XHS_COOKIES", "").strip():
            raise SmokeError("XHS_COOKIES 缺失，pc/spider driver 需要先在环境变量中设置")
        if self.driver not in {"pc", "spider", "cdp", "auto"}:
            raise SmokeError(f"不支持的 XHS_PROVIDER_DRIVER: {self.driver}")
        if not self.post_url:
            raise SmokeError("XHS_TEST_POST_URL 缺失，真实采集 smoke 需要同时验证 keyword 和 post_url")

        self._check_health()

        print(f"driver={self.driver}")
        if self.driver in {"spider", "auto"}:
            print(f"spider_path={'configured' if self.spider_path else 'missing'}")

        summaries: list[TaskSummary] = [
            self._run_single_task(source_type="keyword", source_value=self.keyword, limit_count=5),
            self._run_single_task(source_type="post_url", source_value=self.post_url, limit_count=1),
        ]

        for summary in summaries:
            self._assert_task_run_result(summary)

        posts_total = self._fetch_total("/api/posts")
        comments_total = self._fetch_total("/api/comments")
        leads_total = self._fetch_total("/api/leads")
        daily_report = self._generate_daily_report()
        csv_size = self._export_leads_csv()

        successful_runs = [summary for summary in summaries if summary.status == "success"]
        if successful_runs and posts_total <= 0:
            raise SmokeError("任务状态 success 但 posts 总量未增加，入库验收失败")

        print("\n=== Real Collection Smoke Result ===")
        for summary in summaries:
            print(
                "\n".join(
                    [
                        f"task_id={summary.task_id}",
                        f"source_type={summary.source_type}",
                        f"status={summary.status}",
                        f"collected_posts={summary.collected_posts}",
                        f"collected_comments={summary.collected_comments}",
                        f"post_count={summary.post_count}",
                        f"comment_count={summary.comment_count}",
                        f"lead_count={summary.lead_count}",
                        f"discovered_competitor_count={summary.discovered_competitor_count}",
                        f"error_message={summary.error_message or ''}",
                        "---",
                    ]
                )
            )

        print(f"posts_total={posts_total}")
        print(f"comments_total={comments_total}")
        print(f"leads_total={leads_total}")
        print(f"daily_report_date={daily_report.get('report_date')}")
        print(f"daily_report_id={daily_report.get('id')}")
        print(f"leads_csv_bytes={csv_size}")

    def _check_health(self) -> None:
        status, raw = self.client.request_raw("GET", "/health")
        if status != 200:
            raise SmokeError(f"/health 异常，HTTP {status}")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise SmokeError("/health 返回非 JSON") from error

        if payload.get("status") != "ok":
            raise SmokeError("后端未就绪，/health != ok")

    def _run_single_task(self, source_type: str, source_value: str, limit_count: int) -> TaskSummary:
        create_resp = self.client.request_json(
            "POST",
            "/api/collection/tasks",
            payload={
                "platform": "xhs",
                "source_type": source_type,
                "source_value": source_value,
                "limit_count": limit_count,
            },
        )
        create_data = create_resp.get("data") or {}
        task_id = create_data.get("id")
        if not isinstance(task_id, int):
            raise SmokeError(f"创建任务失败，未返回 task_id: {create_data}")

        run_resp = self.client.request_json("POST", f"/api/collection/tasks/{task_id}/run")
        if run_resp.get("success") is not True:
            raise SmokeError(f"执行任务失败: task_id={task_id}")

        detail_resp = self.client.request_json("GET", f"/api/collection/tasks/{task_id}")
        detail = detail_resp.get("data") or {}

        return TaskSummary(
            task_id=task_id,
            source_type=source_type,
            status=str(detail.get("status") or "unknown"),
            collected_posts=int(detail.get("collected_posts") or 0),
            collected_comments=int(detail.get("collected_comments") or 0),
            post_count=int(detail.get("post_count") or 0),
            comment_count=int(detail.get("comment_count") or 0),
            lead_count=int(detail.get("lead_count") or 0),
            error_message=detail.get("error_message"),
            discovered_competitor_count=int(detail.get("discovered_competitor_count") or 0),
        )

    def _assert_task_run_result(self, summary: TaskSummary) -> None:
        if summary.status not in {"success", "failed"}:
            raise SmokeError(f"task_id={summary.task_id} 状态异常: {summary.status}")
        if summary.status == "failed" and not summary.error_message:
            raise SmokeError(f"task_id={summary.task_id} 失败但缺少 error_message")
        if summary.status == "success" and summary.post_count <= 0 and summary.collected_posts <= 0:
            raise SmokeError(f"task_id={summary.task_id} success 但没有采集到帖子")

    def _generate_daily_report(self) -> dict[str, Any]:
        response = self.client.request_json("POST", "/api/daily-reports/generate")
        data = response.get("data") or {}
        if data.get("report_date") is None:
            raise SmokeError(f"daily report 生成失败: {data}")
        return data

    def _export_leads_csv(self) -> int:
        status, raw = self.client.request_raw("GET", "/api/leads/export")
        if status != 200:
            raise SmokeError(f"leads csv 导出失败: HTTP {status}")
        if not raw:
            raise SmokeError("leads csv 导出结果为空")
        decoded = raw.decode("utf-8-sig", errors="replace")
        if "线索等级" not in decoded:
            raise SmokeError("leads csv 缺少表头字段: 线索等级")
        return len(raw)

    def _fetch_total(self, path: str) -> int:
        response = self.client.request_json("GET", path, params={"page": 1, "page_size": 1})
        data = response.get("data") or {}
        return int(data.get("total") or 0)


def main() -> int:
    runner = RealCollectionSmoke()
    try:
        runner.run()
        return 0
    except SmokeError as error:
        print(f"[FAIL] {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
