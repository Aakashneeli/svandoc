"""QuickBooks Online export connector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class QuickBooksConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class QuickBooksExportResult:
    realm_id: str
    resource_id: str
    storage_uri: str


def build_quickbooks_payload(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    line_items = payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
    doc_type = str(payload.get("document_type", "")).strip().lower()

    if doc_type == "invoice":
        vendor = payload.get("vendor") if isinstance(payload.get("vendor"), dict) else {}
        identity = payload.get("invoice") if isinstance(payload.get("invoice"), dict) else {}
        vendor_name = str(vendor.get("name", "")).strip() or "Unknown Vendor"
        reference_number = str(identity.get("invoice_number", "")).strip() or str(metadata.get("document_id", "")).strip()
        txn_date = str(identity.get("issue_date", "")).strip()
    elif doc_type == "receipt":
        merchant = payload.get("merchant") if isinstance(payload.get("merchant"), dict) else {}
        identity = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else {}
        vendor_name = str(merchant.get("name", "")).strip() or "Unknown Merchant"
        reference_number = str(identity.get("receipt_number", "")).strip() or str(metadata.get("document_id", "")).strip()
        txn_date = str(identity.get("transaction_date", "")).strip()
    else:
        raise QuickBooksConnectorError("unsupported_document_type")

    currency = str(amounts.get("currency", "")).strip() or "USD"
    tax_amount = _float_or_zero(amounts.get("tax"))
    total_amount = _float_or_zero(amounts.get("total"))
    mapped_lines = []
    for index, item in enumerate(line_items):
        mapped_item = item if isinstance(item, dict) else {}
        mapped_lines.append(
            {
                "Amount": _float_or_zero(mapped_item.get("line_total")),
                "Description": str(mapped_item.get("description", "")).strip() or f"Line {index + 1}",
                "DetailType": "AccountBasedExpenseLineDetail",
                "AccountBasedExpenseLineDetail": {
                    "AccountRef": {"value": "7", "name": "Expenses"},
                },
            }
        )
    if not mapped_lines:
        mapped_lines.append(
            {
                "Amount": total_amount,
                "Description": "Document total",
                "DetailType": "AccountBasedExpenseLineDetail",
                "AccountBasedExpenseLineDetail": {
                    "AccountRef": {"value": "7", "name": "Expenses"},
                },
            }
        )

    mapped: dict[str, Any] = {
        "DocNumber": reference_number,
        "TxnDate": txn_date or None,
        "CurrencyRef": {"value": currency},
        "VendorRef": {"name": vendor_name},
        "Line": mapped_lines,
        "TotalAmt": total_amount,
        "TxnTaxDetail": {"TotalTax": tax_amount},
        "PrivateNote": f"svanDoc document {metadata.get('document_id', '')}",
    }
    return mapped


def export_to_quickbooks(
    *,
    access_token: str,
    realm_id: str,
    payload: dict[str, Any],
    timeout_seconds: float = 15.0,
    api_base_url: str = "https://quickbooks.api.intuit.com",
) -> QuickBooksExportResult:
    normalized_payload = build_quickbooks_payload(payload)
    endpoint = (
        f"{api_base_url.rstrip('/')}/v3/company/{realm_id}/purchase"
        "?minorversion=75"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(endpoint, headers=headers, json=normalized_payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise QuickBooksConnectorError(f"quickbooks_export_failed:{exc}") from exc

    purchase = body.get("Purchase") if isinstance(body, dict) else None
    if not isinstance(purchase, dict):
        raise QuickBooksConnectorError("quickbooks_export_failed:missing_purchase")

    resource_id = str(purchase.get("Id", "")).strip()
    if not resource_id:
        raise QuickBooksConnectorError("quickbooks_export_failed:missing_purchase_id")

    return QuickBooksExportResult(
        realm_id=realm_id,
        resource_id=resource_id,
        storage_uri=f"quickbooks://{realm_id}/{resource_id}",
    )


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
