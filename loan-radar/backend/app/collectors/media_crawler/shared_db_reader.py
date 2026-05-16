"""Shared RawTaskStore reader - 直接读取 MediaCrawler 的 raw_tasks.sqlite3。

当设置了 MEDIA_CRAWLER_RAW_DB_PATH 或 MEDIA_CRAWLER_HOME 时，
loan-radar 可以直接读取 MediaCrawler 的采集结果数据库，
跳过 HTTP API 调用，实现零延迟数据读取。
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _get_raw_db_path() -> str | None:
    explicit = os.getenv("MEDIA_CRAWLER_RAW_DB_PATH")
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = Path(os.getcwd()) / p
        return str(p)

    mc_home = os.getenv("MEDIA_CRAWLER_HOME")
    if mc_home:
        home = Path(mc_home)
        if not home.is_absolute():
            home = Path(os.getcwd()) / mc_home
        candidate = home / "data" / "raw_tasks.sqlite3"
        if candidate.exists():
            return str(candidate)

    return None


def is_shared_db_available() -> bool:
    path = _get_raw_db_path()
    if not path:
        return False
    return Path(path).exists()


class SharedRawTaskReader:
    """直接读取 MediaCrawler raw_tasks.sqlite3 的轻量 reader。

    不依赖 MediaCrawler 的 Python 包，纯 sqlite3 标准库实现。
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _get_raw_db_path()
        if not self.db_path:
            raise RuntimeError(
                "MEDIA_CRAWLER_RAW_DB_PATH 或 MEDIA_CRAWLER_HOME 未设置，"
                "无法访问 MediaCrawler 共享数据库"
            )
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"MediaCrawler 数据库不存在: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM crawl_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list_raw_posts(
        self,
        task_id: int,
        *,
        page: int = 1,
        page_size: int = 500,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM raw_posts WHERE task_id = ?",
                (task_id,),
            ).fetchone()[0]
            rows = conn.execute(
                """
                SELECT * FROM raw_posts
                WHERE task_id = ?
                ORDER BY id ASC
                LIMIT ? OFFSET ?
                """,
                (task_id, page_size, offset),
            ).fetchall()
        return {
            "items": [_decode_raw_row(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_raw_comments(
        self,
        task_id: int,
        *,
        page: int = 1,
        page_size: int = 500,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM raw_comments WHERE task_id = ?",
                (task_id,),
            ).fetchone()[0]
            rows = conn.execute(
                """
                SELECT * FROM raw_comments
                WHERE task_id = ?
                ORDER BY id ASC
                LIMIT ? OFFSET ?
                """,
                (task_id, page_size, offset),
            ).fetchall()
        return {
            "items": [_decode_raw_row(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_latest_task_for_source(
        self,
        platform: str,
        source_type: str,
        source_value: str,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM crawl_tasks
                WHERE platform = ? AND source_type = ? AND source_value = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (platform, source_type, source_value),
            ).fetchone()
        return _row_to_dict(row) if row else None


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _decode_raw_row(row: sqlite3.Row) -> dict[str, Any]:
    data = _row_to_dict(row)
    try:
        raw = data.get("raw_data")
        if isinstance(raw, str):
            data["raw_data"] = json.loads(raw)
        elif raw is None:
            data["raw_data"] = {}
    except json.JSONDecodeError:
        data["raw_data"] = {}
    return data
