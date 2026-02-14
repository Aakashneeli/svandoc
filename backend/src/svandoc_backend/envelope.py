"""Shared API response envelope helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Request


def utc_timestamp() -> str:
    """Return UTC timestamp with second precision and trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_id_from_request(request: Request) -> str:
    header_value = request.headers.get("x-request-id", "").strip()
    if header_value:
        return header_value
    return f"req_{uuid4().hex}"


def success_envelope(request: Request, data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    envelope_meta = {"api_version": "v1"}
    if meta:
        envelope_meta.update(meta)

    return {
        "status": "success",
        "request_id": request_id_from_request(request),
        "timestamp": utc_timestamp(),
        "data": data,
        "error": None,
        "meta": envelope_meta,
    }
