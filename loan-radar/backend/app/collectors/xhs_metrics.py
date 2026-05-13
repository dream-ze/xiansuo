from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.collectors.base import CollectionAuthError, CollectionNoDataError, CollectionRequestError


@dataclass(frozen=True)
class ErrorClassification:
    level: str
    error_type: str


def classify_provider_error(error: Exception) -> ErrorClassification:
    if isinstance(error, CollectionAuthError):
        return ErrorClassification(level="P1", error_type="auth")

    if isinstance(error, CollectionNoDataError):
        return ErrorClassification(level="P3", error_type="no_data")

    if isinstance(error, CollectionRequestError):
        text = str(error).lower()
        if any(token in text for token in ("timeout", "timed out")):
            return ErrorClassification(level="P2", error_type="timeout")
        if any(token in text for token in ("network", "connection", "dns", "proxy", "ssl")):
            return ErrorClassification(level="P2", error_type="network")
        if any(token in text for token in ("parse", "format", "invalid", "schema")):
            return ErrorClassification(level="P2", error_type="parse")
        return ErrorClassification(level="P2", error_type="request")

    if isinstance(error, ValueError):
        return ErrorClassification(level="P1", error_type="config")

    return ErrorClassification(level="P0", error_type="unexpected")


class DriverMetricsRecorder:
    def __init__(self) -> None:
        self._lock = Lock()
        self._stats: dict[tuple[str, str], dict[str, Any]] = {}

    def record(
        self,
        *,
        driver: str,
        operation: str,
        duration_ms: float,
        success: bool,
        failure_type: str | None = None,
    ) -> None:
        key = (driver, operation)
        with self._lock:
            payload = self._stats.setdefault(
                key,
                {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "duration_ms_total": 0.0,
                    "failure_types": {},
                },
            )
            payload["total"] += 1
            payload["duration_ms_total"] += max(0.0, duration_ms)

            if success:
                payload["success"] += 1
            else:
                payload["failed"] += 1
                if failure_type:
                    failures = payload["failure_types"]
                    failures[failure_type] = int(failures.get(failure_type, 0)) + 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            grouped: dict[str, dict[str, Any]] = {}
            for (driver, operation), payload in self._stats.items():
                total = int(payload["total"])
                success = int(payload["success"])
                failed = int(payload["failed"])
                duration_total = float(payload["duration_ms_total"])
                grouped.setdefault(driver, {})[operation] = {
                    "total": total,
                    "success": success,
                    "failed": failed,
                    "success_rate": (success / total) if total else 0.0,
                    "avg_duration_ms": (duration_total / total) if total else 0.0,
                    "failure_types": dict(payload["failure_types"]),
                }
            return grouped

    def reset(self) -> None:
        with self._lock:
            self._stats.clear()


_GLOBAL_DRIVER_METRICS = DriverMetricsRecorder()


def get_driver_metrics_recorder() -> DriverMetricsRecorder:
    return _GLOBAL_DRIVER_METRICS
