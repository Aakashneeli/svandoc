"""Structured logging helpers for asynchronous worker jobs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from svandoc_backend.logging_sink import configure_structured_logging

WORKER_LOGGER_NAME = "svandoc.worker"
configure_structured_logging()
worker_logger = logging.getLogger(WORKER_LOGGER_NAME)
if worker_logger.level == logging.NOTSET:
    worker_logger.setLevel(logging.INFO)


def emit_worker_log(
    *,
    event: str,
    request_id: str,
    job_id: str,
    document_id: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "event": event,
        "request_id": request_id,
        "job_id": job_id,
        "document_id": document_id,
        "status": status,
    }
    if details is not None:
        payload["details"] = details

    worker_logger.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))
