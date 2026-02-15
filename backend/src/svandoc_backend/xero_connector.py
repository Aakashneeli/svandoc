"""Xero connector with idempotent retries."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class XeroSyncAttempt:
    attempt_number: int
    sync_status: str
    status_code: int | None
    error_message: str | None
    external_reference: str | None = None


@dataclass(frozen=True)
class XeroExportResult:
    tenant_id: str
    invoice_id: str
    storage_uri: str
    attempts: list[XeroSyncAttempt]


class XeroConnectorError(RuntimeError):
    def __init__(self, message: str, *, attempts: list[XeroSyncAttempt]) -> None:
        super().__init__(message)
        self.attempts = attempts


def build_xero_payload(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    line_items = payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
    doc_type = str(payload.get("document_type", "")).strip().lower()

    if doc_type == "invoice":
        party = payload.get("vendor") if isinstance(payload.get("vendor"), dict) else {}
        identity = payload.get("invoice") if isinstance(payload.get("invoice"), dict) else {}
        reference = str(identity.get("invoice_number", "")).strip() or str(metadata.get("document_id", "")).strip()
        date = str(identity.get("issue_date", "")).strip()
    elif doc_type == "receipt":
        party = payload.get("merchant") if isinstance(payload.get("merchant"), dict) else {}
        identity = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else {}
        reference = str(identity.get("receipt_number", "")).strip() or str(metadata.get("document_id", "")).strip()
        date = str(identity.get("transaction_date", "")).strip()
    else:
        raise XeroConnectorError("unsupported_document_type", attempts=[])

    party_name = str(party.get("name", "")).strip() or "Unknown Supplier"
    total = _float_or_zero(amounts.get("total"))
    tax = _float_or_zero(amounts.get("tax"))
    currency = str(amounts.get("currency", "")).strip() or "USD"

    mapped_lines: list[dict[str, Any]] = []
    for index, line_item in enumerate(line_items):
        item = line_item if isinstance(line_item, dict) else {}
        mapped_lines.append(
            {
                "Description": str(item.get("description", "")).strip() or f"Line {index + 1}",
                "Quantity": _float_or_zero(item.get("quantity")) or 1.0,
                "UnitAmount": _float_or_zero(item.get("unit_price")),
                "LineAmount": _float_or_zero(item.get("line_total")),
                "TaxType": "OUTPUT",
            }
        )
    if not mapped_lines:
        mapped_lines.append(
            {
                "Description": "Document total",
                "Quantity": 1.0,
                "UnitAmount": total,
                "LineAmount": total,
                "TaxType": "OUTPUT",
            }
        )

    return {
        "Type": "ACCPAY",
        "Contact": {"Name": party_name},
        "Date": date or None,
        "Reference": reference,
        "CurrencyCode": currency,
        "LineAmountTypes": "Exclusive",
        "LineItems": mapped_lines,
        "TotalTax": tax,
    }


def export_to_xero(
    *,
    access_token: str,
    tenant_id: str,
    payload: dict[str, Any],
    idempotency_key: str,
    max_attempts: int = 3,
    timeout_seconds: float = 15.0,
    retry_backoff_seconds: float = 2.0,
    api_base_url: str = "https://api.xero.com/api.xro/2.0",
) -> XeroExportResult:
    request_payload = build_xero_payload(payload)
    endpoint = f"{api_base_url.rstrip('/')}/Invoices"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "xero-tenant-id": tenant_id,
        "Idempotency-Key": idempotency_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    attempts: list[XeroSyncAttempt] = []
    for attempt in range(1, max_attempts + 1):
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(endpoint, headers=headers, json=request_payload)
        except httpx.HTTPError as exc:
            is_last = attempt >= max_attempts
            attempts.append(
                XeroSyncAttempt(
                    attempt_number=attempt,
                    sync_status="failed" if is_last else "retrying",
                    status_code=None,
                    error_message=str(exc),
                )
            )
            if is_last:
                raise XeroConnectorError(f"xero_export_failed:{exc}", attempts=attempts) from exc
            time.sleep(retry_backoff_seconds * (2 ** (attempt - 1)))
            continue

        status_code = int(response.status_code)
        if 200 <= status_code < 300:
            body = response.json()
            invoices = body.get("Invoices") if isinstance(body, dict) else None
            first_invoice = invoices[0] if isinstance(invoices, list) and invoices else {}
            invoice_id = str(first_invoice.get("InvoiceID", "")).strip()
            if not invoice_id:
                attempts.append(
                    XeroSyncAttempt(
                        attempt_number=attempt,
                        sync_status="failed",
                        status_code=status_code,
                        error_message="missing_invoice_id",
                    )
                )
                raise XeroConnectorError("xero_export_failed:missing_invoice_id", attempts=attempts)
            attempts.append(
                XeroSyncAttempt(
                    attempt_number=attempt,
                    sync_status="synced",
                    status_code=status_code,
                    error_message=None,
                    external_reference=invoice_id,
                )
            )
            return XeroExportResult(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                storage_uri=f"xero://{tenant_id}/{invoice_id}",
                attempts=attempts,
            )

        retryable = status_code in RETRYABLE_STATUS_CODES
        is_last = attempt >= max_attempts
        attempts.append(
            XeroSyncAttempt(
                attempt_number=attempt,
                sync_status="failed" if (is_last or not retryable) else "retrying",
                status_code=status_code,
                error_message=f"http_status_{status_code}",
            )
        )
        if not retryable or is_last:
            raise XeroConnectorError(f"xero_export_failed:http_status_{status_code}", attempts=attempts)
        time.sleep(retry_backoff_seconds * (2 ** (attempt - 1)))

    raise XeroConnectorError("xero_export_failed:exhausted_retries", attempts=attempts)


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
