# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


RawKind = Literal["post", "comment"]


class RawTaskStore:
    """SQLite-backed store for crawl task metadata and raw collection results."""

    def __init__(self, db_path: str | Path | None = None):
        default_path = Path(__file__).parent.parent.parent / "data" / "raw_tasks.sqlite3"
        env_path = os.getenv("MEDIA_CRAWLER_RAW_DB_PATH")
        self.db_path = Path(db_path or env_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_value TEXT NOT NULL,
                    crawler_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    post_count INTEGER NOT NULL DEFAULT 0,
                    comment_count INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT,
                    finished_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_value TEXT NOT NULL,
                    raw_id TEXT NOT NULL,
                    post_raw_id TEXT,
                    url TEXT,
                    content_text TEXT,
                    author_name TEXT,
                    published_at TEXT,
                    raw_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(task_id, platform, raw_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_value TEXT NOT NULL,
                    raw_id TEXT NOT NULL,
                    post_raw_id TEXT,
                    url TEXT,
                    content_text TEXT,
                    author_name TEXT,
                    published_at TEXT,
                    raw_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(task_id, platform, raw_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_posts_task ON raw_posts(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_comments_task ON raw_comments(task_id)")

    def create_task(
        self,
        *,
        platform: str,
        source_type: str,
        source_value: str,
        crawler_type: str,
    ) -> dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO crawl_tasks (
                    platform, source_type, source_value, crawler_type, status,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (platform, source_type, source_value, crawler_type, now, now),
            )
            task_id = int(cursor.lastrowid)
        task = self.get_task(task_id)
        if task is None:
            raise RuntimeError(f"created crawl task {task_id} could not be loaded")
        return task

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM crawl_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def mark_running(self, task_id: int) -> None:
        now = _now()
        self._update_task(
            task_id,
            status="running",
            started_at=now,
            updated_at=now,
        )

    def mark_success(self, task_id: int) -> None:
        now = _now()
        with self._connect() as conn:
            post_count = conn.execute(
                "SELECT COUNT(*) FROM raw_posts WHERE task_id = ?",
                (task_id,),
            ).fetchone()[0]
            comment_count = conn.execute(
                "SELECT COUNT(*) FROM raw_comments WHERE task_id = ?",
                (task_id,),
            ).fetchone()[0]
            conn.execute(
                """
                UPDATE crawl_tasks
                SET status = 'success',
                    error_message = NULL,
                    post_count = ?,
                    comment_count = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (post_count, comment_count, now, now, task_id),
            )

    def mark_failed(self, task_id: int, error_message: str) -> None:
        now = _now()
        self._update_task(
            task_id,
            status="failed",
            error_message=error_message,
            finished_at=now,
            updated_at=now,
        )

    def insert_raw_post(self, **kwargs: Any) -> None:
        self._insert_raw("post", **kwargs)

    def insert_raw_comment(self, **kwargs: Any) -> None:
        self._insert_raw("comment", **kwargs)

    def list_raw_posts(self, task_id: int, *, page: int = 1, page_size: int = 100) -> dict[str, Any]:
        return self._list_raw("post", task_id, page=page, page_size=page_size)

    def list_raw_comments(self, task_id: int, *, page: int = 1, page_size: int = 100) -> dict[str, Any]:
        return self._list_raw("comment", task_id, page=page, page_size=page_size)

    def _update_task(self, task_id: int, **fields: Any) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values())
        values.append(task_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE crawl_tasks SET {assignments} WHERE id = ?",
                values,
            )

    def _insert_raw(self, kind: RawKind, **kwargs: Any) -> None:
        table = "raw_posts" if kind == "post" else "raw_comments"
        raw_data = kwargs.get("raw_data") or {}
        now = _now()
        values = (
            kwargs["task_id"],
            kwargs["platform"],
            kwargs["source_type"],
            kwargs["source_value"],
            kwargs["raw_id"],
            kwargs.get("post_raw_id"),
            kwargs.get("url"),
            kwargs.get("content_text"),
            kwargs.get("author_name"),
            kwargs.get("published_at"),
            json.dumps(raw_data, ensure_ascii=False),
            now,
        )
        with self._connect() as conn:
            conn.execute(
                f"""
                INSERT OR IGNORE INTO {table} (
                    task_id, platform, source_type, source_value, raw_id,
                    post_raw_id, url, content_text, author_name, published_at,
                    raw_data, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

    def _list_raw(self, kind: RawKind, task_id: int, *, page: int, page_size: int) -> dict[str, Any]:
        table = "raw_posts" if kind == "post" else "raw_comments"
        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE task_id = ?",
                (task_id,),
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT * FROM {table}
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _decode_raw_row(row: sqlite3.Row) -> dict[str, Any]:
    data = _row_to_dict(row)
    try:
        data["raw_data"] = json.loads(data.get("raw_data") or "{}")
    except json.JSONDecodeError:
        data["raw_data"] = {}
    return data
