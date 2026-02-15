"""Outbound webhook delivery with signed payloads and retry logging."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from svandoc_backend.models.webhook_delivery_log import WebhookDeliveryLog

DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2.0


def configured_webhook_endpoints() -> list[str]:
    raw = os.getenv("WEBHOOK_ENDPOINTS", "")
    return [value.strip() for value in raw.split(",") if value.strip()]


def webhook_signing_secret() -> str:
    return os.getenv("WEBHOOK_SIGNING_SECRET", "").strip()


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _event_payload(event_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    occurred_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "data": data,
    }


def _serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def _build_signature(payload_json: str, signing_secret: str) -> str:
    digest = hmac.new(
        key=signing_secret.encode("utf-8"),
        msg=payload_json.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def _persist_delivery_log(
    session: Session,
    *,
    event_id: str,
    event_type: str,
    endpoint_url: str,
    attempt_number: int,
    delivery_status: str,
    payload_json: str,
    signature: str,
    response_status_code: int | None,
    error_message: str | None,
) -> None:
    session.add(
        WebhookDeliveryLog(
            id=str(uuid4()),
            event_id=event_id,
            event_type=event_type,
            endpoint_url=endpoint_url,
            attempt_number=attempt_number,
            delivery_status=delivery_status,
            response_status_code=response_status_code,
            error_message=error_message,
            signature=signature,
            payload_json=payload_json,
        )
    )
    session.commit()


def _deliver_to_endpoint(
    session: Session,
    *,
    event_id: str,
    event_type: str,
    endpoint_url: str,
    payload_json: str,
    signature: str,
) -> bool:
    max_attempts = _int_env("WEBHOOK_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)
    timeout_seconds = _float_env("WEBHOOK_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    retry_backoff_seconds = _float_env("WEBHOOK_RETRY_BACKOFF_SECONDS", DEFAULT_RETRY_BACKOFF_SECONDS)
    headers = {
        "Content-Type": "application/json",
        "X-SvanDoc-Event": event_type,
        "X-SvanDoc-Event-Id": event_id,
        "X-SvanDoc-Signature": signature,
    }

    for attempt in range(1, max_attempts + 1):
        response_status: int | None = None
        error_message: str | None = None
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(endpoint_url, headers=headers, content=payload_json.encode("utf-8"))
            response_status = int(response.status_code)
            delivered = 200 <= response.status_code < 300
            if not delivered:
                error_message = f"http_status_{response.status_code}"
        except httpx.HTTPError as exc:
            delivered = False
            error_message = str(exc)

        _persist_delivery_log(
            session,
            event_id=event_id,
            event_type=event_type,
            endpoint_url=endpoint_url,
            attempt_number=attempt,
            delivery_status="delivered" if delivered else "failed",
            payload_json=payload_json,
            signature=signature,
            response_status_code=response_status,
            error_message=error_message,
        )
        if delivered:
            return True
        if attempt < max_attempts:
            time.sleep(retry_backoff_seconds * (2 ** (attempt - 1)))

    return False


def deliver_webhook_event(session: Session, *, event_type: str, data: dict[str, Any]) -> int:
    endpoints = configured_webhook_endpoints()
    secret = webhook_signing_secret()
    if not endpoints or not secret:
        return 0

    event_id = str(uuid4())
    payload = _event_payload(event_id=event_id, event_type=event_type, data=data)
    payload_json = _serialize_payload(payload)
    signature = _build_signature(payload_json, secret)

    delivered_count = 0
    for endpoint in endpoints:
        if _deliver_to_endpoint(
            session,
            event_id=event_id,
            event_type=event_type,
            endpoint_url=endpoint,
            payload_json=payload_json,
            signature=signature,
        ):
            delivered_count += 1
    return delivered_count
