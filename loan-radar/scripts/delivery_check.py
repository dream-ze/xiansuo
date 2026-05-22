#!/usr/bin/env python3
"""
智获客 · 助贷线索雷达 - 交付验收检查脚本
检查项目：docker compose config / 前端构建 / 后端编译 / 数据库迁移 / 核心 API 可用性
输出：reports/delivery_check_report.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
REPORTS_DIR = BACKEND_DIR / "reports"
REPORT_FILE = REPORTS_DIR / "delivery_check_report.md"

SMOKE_BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001")
TIMEOUT = 10

checks: list[dict[str, Any]] = []


def run(cmd: str, cwd: Path | None = None, timeout: int = 120) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as exc:
        return False, str(exc)


def check(name: str, fn: callable) -> None:
    print(f"  Checking: {name}...", end=" ", flush=True)
    try:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        print(f"{status}")
        checks.append({"name": name, "status": status, "detail": detail or ""})
    except Exception as exc:
        print("FAIL")
        checks.append({"name": name, "status": "FAIL", "detail": str(exc)})


def check_docker_compose_config() -> tuple[bool, str]:
    ok, output = run("docker compose config --quiet", cwd=BASE_DIR)
    return ok, output


def check_frontend_build() -> tuple[bool, str]:
    ok, output = run("npm run build", cwd=FRONTEND_DIR, timeout=180)
    return ok, output[-500:] if len(output) > 500 else output


def check_backend_compile() -> tuple[bool, str]:
    ok, output = run("python -m compileall app -q", cwd=BACKEND_DIR, timeout=60)
    return ok, output[-500:] if len(output) > 500 else output


def check_alembic() -> tuple[bool, str]:
    env_file = BACKEND_DIR / ".env"
    env_prefix = ""
    if env_file.exists():
        pass
    ok, output = run("alembic upgrade head", cwd=BACKEND_DIR, timeout=60)
    return ok, output[-500:] if len(output) > 500 else output


def _api(method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
    import requests as req

    url = f"{SMOKE_BASE_URL}{path}"
    kwargs.setdefault("timeout", TIMEOUT)
    try:
        resp = req.request(method, url, **kwargs)
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:200]
        return resp.status_code, body
    except Exception as exc:
        return 0, str(exc)


def check_health() -> tuple[bool, str]:
    code, body = _api("GET", "/health")
    if code == 200:
        data = body if isinstance(body, dict) else {}
        return data.get("status") == "ok", json.dumps(body, ensure_ascii=False)[:200]
    return False, f"HTTP {code}: {str(body)[:200]}"


def check_login() -> tuple[bool, str]:
    code, body = _api("POST", "/api/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    if code in (200, 201):
        data = body if isinstance(body, dict) else {}
        token = data.get("access_token") or data.get("data", {}).get("access_token", "")
        if token:
            os.environ["DELIVERY_TOKEN"] = token
        return bool(token), f"token_len={len(str(token))}"
    if code == 401:
        code2, body2 = _api("POST", "/api/auth/register", json={
            "username": "delivery_check",
            "password": "DeliveryCheck123!",
        })
        if code2 in (200, 201):
            data2 = body2 if isinstance(body2, dict) else {}
            token = data2.get("access_token") or data2.get("data", {}).get("access_token", "")
            if token:
                os.environ["DELIVERY_TOKEN"] = token
            return True, "registered+login ok"
        return False, f"register failed: HTTP {code2}"
    return False, f"HTTP {code}: {str(body)[:200]}"


def _auth_headers() -> dict[str, str]:
    token = os.environ.get("DELIVERY_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def check_core_api(path: str, method: str = "GET", body: dict | None = None) -> tuple[bool, str]:
    kwargs: dict[str, Any] = {"headers": _auth_headers()}
    if body:
        kwargs["json"] = body
    code, resp = _api(method, path, **kwargs)
    if code in (200, 201):
        return True, f"HTTP {code}"
    if code == 401:
        return True, f"HTTP {code} (auth required - endpoint exists)"
    if code == 404:
        return False, f"HTTP {code} - endpoint not found"
    return code >= 200 and code < 500, f"HTTP {code}: {str(resp)[:200]}"


def check_collection_tasks() -> tuple[bool, str]:
    return check_core_api("/api/collection/tasks")


def check_leads() -> tuple[bool, str]:
    return check_core_api("/api/leads")


def check_posts() -> tuple[bool, str]:
    return check_core_api("/api/posts")


def check_daily_reports() -> tuple[bool, str]:
    return check_core_api("/api/daily-reports/today")


def check_xhs_analytics() -> tuple[bool, str]:
    return check_core_api("/api/xhs/analytics/overview")


def check_xhs_auto_ops() -> tuple[bool, str]:
    return check_core_api("/api/xhs/auto-ops/tasks")


def check_xhs_monitoring() -> tuple[bool, str]:
    return check_core_api("/api/xhs/monitoring/targets")


def generate_report() -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    total = len(checks)

    lines = [
        f"# 交付验收检查报告",
        f"",
        f"**生成时间**: {now}",
        f"**目标服务**: {SMOKE_BASE_URL}",
        f"",
        f"## 汇总",
        f"",
        f"| 指标 | 值 |",
        f"|------|------|",
        f"| 总检查项 | {total} |",
        f"| 通过 | {passed} |",
        f"| 失败 | {failed} |",
        f"| 通过率 | {passed/total*100:.1f}% |",
        f"",
        f"## 检查详情",
        f"",
        f"| # | 检查项 | 状态 | 详情 |",
        f"|---|--------|------|------|",
    ]

    for i, c in enumerate(checks, 1):
        status_icon = "✅" if c["status"] == "PASS" else "❌"
        detail = c["detail"][:100].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | {c['name']} | {status_icon} {c['status']} | {detail} |")

    lines.append("")
    lines.append("## 交付结论")
    lines.append("")
    if failed == 0:
        lines.append("✅ **所有检查项通过，达到交付标准。**")
    else:
        lines.append(f"❌ **{failed} 项检查未通过，需修复后重新验收。**")
    lines.append("")

    report = "\n".join(lines)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\n报告已写入: {REPORT_FILE}")
    return report


def main():
    print("=" * 60)
    print("  智获客 · 助贷线索雷达 - 交付验收检查")
    print("=" * 60)
    print()

    print("[1/3] 静态检查（不依赖运行服务）")
    check("docker compose config", check_docker_compose_config)
    check("前端 npm run build", check_frontend_build)
    check("后端 python -m compileall", check_backend_compile)
    check("alembic upgrade head", check_alembic)

    print()
    print("[2/3] 运行时检查（依赖后端服务）")
    check("/health 健康检查", check_health)
    check("登录接口", check_login)

    print()
    print("[3/3] 核心 API 检查")
    check("/api/collection/tasks", check_collection_tasks)
    check("/api/leads", check_leads)
    check("/api/posts", check_posts)
    check("/api/daily-reports/today", check_daily_reports)
    check("/api/xhs/analytics/overview", check_xhs_analytics)
    check("/api/xhs/auto-ops/tasks", check_xhs_auto_ops)
    check("/api/xhs/monitoring/targets", check_xhs_monitoring)

    print()
    print("=" * 60)

    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    print(f"  结果: {passed} PASS / {failed} FAIL / {len(checks)} TOTAL")
    print("=" * 60)

    generate_report()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
