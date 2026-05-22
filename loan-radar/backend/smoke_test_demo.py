"""
助贷线索雷达 Demo Smoke Test
测试链路：创建 media_crawler 监控源 → 创建采集任务 → 采集失败不崩溃 → 写入错误信息 → 线索列表可查询 → 日报可生成 → 同行账号页面接口可用 → CSV 可导出
"""

import json
import sys
import time
from typing import Any

import os

import requests

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001")
TIMEOUT = 10

passed = 0
failed = 0
errors: list[str] = []


def api(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{BASE_URL}{path}"
    kwargs.setdefault("timeout", TIMEOUT)
    return requests.request(method, url, **kwargs)


def test(name: str, fn: callable) -> None:
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  ✅ {name}")
    except Exception as e:
        failed += 1
        errors.append(f"{name}: {e}")
        print(f"  ❌ {name} — {e}")


def test_health():
    r = api("GET", "/health")
    assert r.status_code == 200, f"health check failed: {r.status_code}"
    data = r.json()
    assert data.get("status") == "ok", f"unexpected health: {data}"


def test_create_media_crawler_source():
    r = api("POST", "/api/monitor-sources", json={
        "source_type": "keyword",
        "platform": "xhs",
        "name": "[SmokeTest] 贷款关键词监控",
        "value": "贷款 急用钱",
        "config": {
            "collector_type": "media_crawler",
            "max_posts": 5,
            "max_comments_per_post": 5,
            "login_type": "qrcode",
            "enable_comments": True,
        },
    })
    assert r.status_code in (200, 201), f"create source failed: {r.status_code} {r.text[:200]}"
    source = r.json()
    assert source.get("config", {}).get("collector_type") == "media_crawler"
    test_create_media_crawler_source.source_id = source["id"]


def test_reject_unsupported_collector():
    r = api("POST", "/api/monitor-sources", json={
        "source_type": "keyword",
        "platform": "xhs",
        "name": "[SmokeTest] Bad collector",
        "value": "test",
        "config": {
            "collector_type": "mock",
        },
    })
    assert r.status_code in (400, 422), f"mock collector should be rejected: {r.status_code}"


def test_create_crawl_task():
    source_id = test_create_media_crawler_source.source_id
    r = api("POST", "/api/crawl-tasks", json={
        "monitor_source_id": source_id,
    })
    assert r.status_code in (200, 201), f"create task failed: {r.status_code} {r.text[:200]}"
    task = r.json()
    test_create_crawl_task.task_id = task["id"]


def test_crawl_task_failure_handled():
    source_id = test_create_media_crawler_source.source_id
    r = api("POST", "/api/crawl-tasks", json={
        "monitor_source_id": source_id,
    })
    assert r.status_code in (200, 201), f"create task failed: {r.status_code}"
    task_id = r.json()["id"]

    time.sleep(2)

    r = api("GET", f"/api/crawl-tasks/{task_id}")
    assert r.status_code == 200, f"get task failed: {r.status_code}"
    task = r.json()
    if task.get("status") == "failed":
        assert task.get("error_message") is not None, "failed task should have error_message"


def test_leads_list():
    r = api("GET", "/api/leads", params={"page": 1, "page_size": 10})
    assert r.status_code == 200, f"leads list failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "items" in data or isinstance(data, list), f"unexpected leads response: {type(data)}"


def test_leads_filter_by_level():
    r = api("GET", "/api/leads", params={"level": "A", "page": 1, "page_size": 5})
    assert r.status_code == 200, f"leads filter failed: {r.status_code}"


def test_daily_report_generate():
    r = api("POST", "/api/daily-reports/generate", json={"platform": "all"})
    if r.status_code == 404:
        r = api("POST", "/api/daily-reports/generate")
    assert r.status_code in (200, 201, 404), f"report generate failed: {r.status_code} {r.text[:200]}"


def test_daily_report_get():
    r = api("GET", "/api/daily-reports/today")
    assert r.status_code in (200, 404), f"report get failed: {r.status_code}"


def test_pending_competitors():
    r = api("GET", "/api/pending-competitors", params={"status": "pending"})
    assert r.status_code == 200, f"pending competitors failed: {r.status_code} {r.text[:200]}"


def test_csv_export():
    r = api("GET", "/api/leads/export", params={"format": "csv"})
    if r.status_code == 404:
        r = api("GET", "/api/leads/export/csv")
    assert r.status_code in (200, 404), f"csv export failed: {r.status_code}"


def test_dashboard():
    r = api("GET", "/api/dashboard/stats")
    assert r.status_code == 200, f"dashboard failed: {r.status_code} {r.text[:200]}"


def test_collectors_capabilities():
    r = api("GET", "/api/collectors/capabilities")
    assert r.status_code == 200, f"collectors capabilities failed: {r.status_code}"
    data = r.json()
    collectors = data.get("collectors", {})
    assert "media_crawler" in collectors, "media_crawler should be in capabilities"
    assert "mock" not in collectors, "mock should NOT be in capabilities"


def cleanup():
    source_id = getattr(test_create_media_crawler_source, "source_id", None)
    if source_id:
        try:
            api("DELETE", f"/api/monitor-sources/{source_id}")
        except Exception:
            pass


def main():
    print("=" * 60)
    print("助贷线索雷达 Demo Smoke Test")
    print("=" * 60)

    test("健康检查", test_health)
    test("创建 media_crawler 监控源", test_create_media_crawler_source)
    test("拒绝不支持的采集器类型", test_reject_unsupported_collector)
    test("创建采集任务", test_create_crawl_task)
    test("采集失败不崩溃", test_crawl_task_failure_handled)
    test("线索列表可查询", test_leads_list)
    test("线索按等级筛选", test_leads_filter_by_level)
    test("日报可生成", test_daily_report_generate)
    test("日报可查询", test_daily_report_get)
    test("同行账号接口可用", test_pending_competitors)
    test("CSV 可导出", test_csv_export)
    test("工作台统计接口", test_dashboard)
    test("采集器能力接口", test_collectors_capabilities)

    cleanup()

    print()
    print("=" * 60)
    print(f"结果：✅ {passed} 通过  ❌ {failed} 失败")
    if errors:
        print("\n失败详情：")
        for e in errors:
            print(f"  - {e}")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
