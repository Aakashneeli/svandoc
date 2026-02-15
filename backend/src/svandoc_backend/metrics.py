"""In-process metrics registry for API and worker instrumentation."""

from __future__ import annotations

import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

_LOCK = threading.Lock()
_LATENCY_WINDOW = 500

_METRICS: dict[str, Any] = {
    "api_requests_total": 0,
    "api_errors_total": 0,
    "api_latency_ms_total": 0.0,
    "api_latency_samples": deque(maxlen=_LATENCY_WINDOW),
    "jobs_processed_total": 0,
    "jobs_failed_total": 0,
    "jobs_review_required_total": 0,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _queue_backend_mode() -> str:
    mode = os.environ.get("QUEUE_BACKEND", "celery").strip().lower()
    return mode or "celery"


def _redis_url() -> str:
    value = os.environ.get("REDIS_URL", "redis://localhost:6379/0").strip()
    return value or "redis://localhost:6379/0"


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    rank = int(round((len(sorted_values) - 1) * percentile))
    return sorted_values[max(0, min(rank, len(sorted_values) - 1))]


def record_api_request(*, duration_ms: int, status_code: int) -> None:
    with _LOCK:
        _METRICS["api_requests_total"] += 1
        _METRICS["api_latency_ms_total"] += float(duration_ms)
        _METRICS["api_latency_samples"].append(float(duration_ms))
        if status_code >= 400:
            _METRICS["api_errors_total"] += 1


def record_job_result(status: str) -> None:
    normalized = (status or "").strip().lower()
    with _LOCK:
        _METRICS["jobs_processed_total"] += 1
        if normalized == "failed":
            _METRICS["jobs_failed_total"] += 1
        if normalized == "review_required":
            _METRICS["jobs_review_required_total"] += 1


def _queue_depth_snapshot() -> dict[str, Any]:
    if _queue_backend_mode() == "disabled":
        return {"available": True, "depth": 0, "status": "disabled"}
    try:
        client = Redis.from_url(_redis_url(), socket_connect_timeout=2, socket_timeout=2)
        depth = int(client.llen("celery"))
    except RedisError as exc:
        return {"available": False, "depth": None, "status": f"error:{exc.__class__.__name__}"}
    return {"available": True, "depth": depth, "status": "ok"}


def metrics_snapshot() -> dict[str, Any]:
    with _LOCK:
        request_count = int(_METRICS["api_requests_total"])
        error_count = int(_METRICS["api_errors_total"])
        latency_total = float(_METRICS["api_latency_ms_total"])
        latencies = list(_METRICS["api_latency_samples"])
        jobs_processed = int(_METRICS["jobs_processed_total"])
        jobs_failed = int(_METRICS["jobs_failed_total"])
        jobs_review_required = int(_METRICS["jobs_review_required_total"])

    avg_latency = (latency_total / request_count) if request_count else 0.0
    queue_depth = _queue_depth_snapshot()

    return {
        "timestamp": _utc_now(),
        "api": {
            "requests_total": request_count,
            "errors_total": error_count,
            "error_rate": round((error_count / request_count), 4) if request_count else 0.0,
            "latency_ms": {
                "avg": round(avg_latency, 2),
                "p95": round(_percentile(latencies, 0.95), 2),
                "sample_size": len(latencies),
            },
        },
        "jobs": {
            "processed_total": jobs_processed,
            "failed_total": jobs_failed,
            "review_required_total": jobs_review_required,
        },
        "queue": queue_depth,
    }


def reset_metrics_for_tests() -> None:
    with _LOCK:
        _METRICS["api_requests_total"] = 0
        _METRICS["api_errors_total"] = 0
        _METRICS["api_latency_ms_total"] = 0.0
        _METRICS["api_latency_samples"].clear()
        _METRICS["jobs_processed_total"] = 0
        _METRICS["jobs_failed_total"] = 0
        _METRICS["jobs_review_required_total"] = 0
