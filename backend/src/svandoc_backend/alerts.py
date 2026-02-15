"""Threshold-based alert evaluation for operational monitoring."""

from __future__ import annotations

import os
from typing import Any


def _read_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        return default
    if parsed < 0:
        return default
    return parsed


def evaluate_alerts(metrics: dict[str, Any]) -> dict[str, Any]:
    failed_recent = int(metrics.get("jobs", {}).get("failed_recent_window", 0))
    failed_recent_threshold = _read_int_env("ALERT_FAILED_RECENT_THRESHOLD", 5)
    queue_depth = metrics.get("queue", {}).get("depth")
    queue_backlog_threshold = _read_int_env("ALERT_QUEUE_BACKLOG_DEPTH", 25)
    error_rate = float(metrics.get("api", {}).get("error_rate", 0.0))
    error_rate_threshold = _read_float_env("ALERT_API_ERROR_RATE_THRESHOLD", 0.2)

    active_alerts: list[dict[str, Any]] = []

    if failed_recent >= failed_recent_threshold:
        active_alerts.append(
            {
                "code": "REPEATED_JOB_FAILURES",
                "severity": "high",
                "message": "Recent job failures crossed the configured threshold.",
                "current": failed_recent,
                "threshold": failed_recent_threshold,
            }
        )

    if isinstance(queue_depth, int) and queue_depth >= queue_backlog_threshold:
        active_alerts.append(
            {
                "code": "QUEUE_BACKLOG",
                "severity": "medium",
                "message": "Queue backlog depth crossed the configured threshold.",
                "current": queue_depth,
                "threshold": queue_backlog_threshold,
            }
        )

    if error_rate >= error_rate_threshold:
        active_alerts.append(
            {
                "code": "API_ERROR_RATE_HIGH",
                "severity": "medium",
                "message": "API error rate crossed the configured threshold.",
                "current": round(error_rate, 4),
                "threshold": error_rate_threshold,
            }
        )

    return {
        "status": "alerting" if active_alerts else "ok",
        "active": active_alerts,
        "thresholds": {
            "failed_recent_threshold": failed_recent_threshold,
            "queue_backlog_depth": queue_backlog_threshold,
            "api_error_rate_threshold": error_rate_threshold,
        },
    }
