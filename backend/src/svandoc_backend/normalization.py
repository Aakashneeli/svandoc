"""Normalization helpers for canonical invoice/receipt extraction payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from svandoc_backend.table_extraction import extract_line_items_from_tables

SCHEMA_VERSION = "1.0.0"


def normalize_ocr_output(
    *,
    doc_type: str,
    document_id: str,
    source_file_name: str,
    page_count: int,
    raw_text: str,
    structured_payload: dict[str, Any],
    review_required: bool,
) -> dict[str, Any]:
    normalized_doc_type = "receipt" if (doc_type or "").strip().lower() == "receipt" else "invoice"
    if normalized_doc_type == "receipt":
        return _normalize_receipt_payload(
            document_id=document_id,
            source_file_name=source_file_name,
            page_count=page_count,
            raw_text=raw_text,
            structured_payload=structured_payload,
            review_required=review_required,
        )
    return _normalize_invoice_payload(
        document_id=document_id,
        source_file_name=source_file_name,
        page_count=page_count,
        raw_text=raw_text,
        structured_payload=structured_payload,
        review_required=review_required,
    )


def _normalize_invoice_payload(
    *,
    document_id: str,
    source_file_name: str,
    page_count: int,
    raw_text: str,
    structured_payload: dict[str, Any],
    review_required: bool,
) -> dict[str, Any]:
    vendor_name = _coerce_string(structured_payload.get("vendor_name") or _nested_get(structured_payload, "vendor", "name"))
    invoice_number = _coerce_string(structured_payload.get("invoice_number"))
    issue_date = _coerce_date(structured_payload.get("issue_date"))

    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "invoice",
        "metadata": _build_metadata(document_id=document_id, source_file_name=source_file_name, page_count=page_count),
        "vendor": {
            "name": vendor_name or "UNKNOWN_VENDOR",
            "tax_id": _nullable_string(structured_payload.get("vendor_tax_id")),
            "address": _nullable_string(structured_payload.get("vendor_address")),
            "email": _nullable_string(structured_payload.get("vendor_email")),
        },
        "customer": _normalize_invoice_customer(structured_payload),
        "invoice": {
            "invoice_number": invoice_number or "UNKNOWN-INVOICE",
            "issue_date": issue_date or _today_date(),
            "due_date": _nullable_date(structured_payload.get("due_date")),
            "purchase_order_number": _nullable_string(structured_payload.get("purchase_order_number")),
        },
        "amounts": {
            "currency": _coerce_currency(structured_payload.get("currency")),
            "subtotal": _coerce_number(structured_payload.get("subtotal")),
            "tax": _coerce_number(structured_payload.get("tax")),
            "shipping": _optional_number(structured_payload.get("shipping")),
            "discount": _optional_number(structured_payload.get("discount")),
            "total": _coerce_number(structured_payload.get("total")),
        },
        "line_items": _normalize_line_items(
            structured_payload.get("line_items"),
            include_category=False,
            structured_payload=structured_payload,
        ),
        "payment_terms": _nullable_string(structured_payload.get("payment_terms")),
        "confidence": {"overall": 0.0, "fields": {}},
        "raw_text": str(raw_text or ""),
        "review_required": bool(review_required),
        "warnings": [],
    }


def _normalize_receipt_payload(
    *,
    document_id: str,
    source_file_name: str,
    page_count: int,
    raw_text: str,
    structured_payload: dict[str, Any],
    review_required: bool,
) -> dict[str, Any]:
    merchant_name = _coerce_string(structured_payload.get("merchant_name") or _nested_get(structured_payload, "merchant", "name"))
    receipt_number = _coerce_string(structured_payload.get("receipt_number"))
    transaction_date = _coerce_date(structured_payload.get("transaction_date"))

    return {
        "schema_version": SCHEMA_VERSION,
        "document_type": "receipt",
        "metadata": _build_metadata(document_id=document_id, source_file_name=source_file_name, page_count=page_count),
        "merchant": {
            "name": merchant_name or "UNKNOWN_MERCHANT",
            "tax_id": _nullable_string(structured_payload.get("merchant_tax_id")),
            "address": _nullable_string(structured_payload.get("merchant_address")),
            "phone": _nullable_string(structured_payload.get("merchant_phone")),
        },
        "receipt": {
            "receipt_number": receipt_number or "UNKNOWN-RECEIPT",
            "transaction_date": transaction_date or _today_date(),
            "transaction_time": _nullable_string(structured_payload.get("transaction_time")),
            "payment_method": _nullable_string(structured_payload.get("payment_method")),
        },
        "amounts": {
            "currency": _coerce_currency(structured_payload.get("currency")),
            "subtotal": _coerce_number(structured_payload.get("subtotal")),
            "tax": _coerce_number(structured_payload.get("tax")),
            "tip": _optional_number(structured_payload.get("tip")),
            "total": _coerce_number(structured_payload.get("total")),
        },
        "line_items": _normalize_line_items(
            structured_payload.get("line_items"),
            include_category=True,
            structured_payload=structured_payload,
        ),
        "confidence": {"overall": 0.0, "fields": {}},
        "raw_text": str(raw_text or ""),
        "review_required": bool(review_required),
        "warnings": [],
    }


def _normalize_invoice_customer(payload: dict[str, Any]) -> dict[str, Any] | None:
    customer_name = _coerce_string(payload.get("customer_name") or _nested_get(payload, "customer", "name"))
    customer_address = _nullable_string(payload.get("customer_address") or _nested_get(payload, "customer", "address"))
    if not customer_name and customer_address is None:
        return None
    return {
        "name": customer_name or "UNKNOWN_CUSTOMER",
        "address": customer_address,
    }


def _normalize_line_items(
    value: Any,
    *,
    include_category: bool,
    structured_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    advanced_table_items = extract_line_items_from_tables(
        structured_payload=structured_payload,
        include_category=include_category,
    )
    if advanced_table_items:
        value = advanced_table_items

    if not isinstance(value, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        line_item: dict[str, Any] = {
            "description": _coerce_string(item.get("description")) or "UNSPECIFIED_ITEM",
            "quantity": _coerce_number(item.get("quantity") if item.get("quantity") is not None else item.get("qty"), 1.0),
            "unit_price": _coerce_number(item.get("unit_price"), 0.0),
            "line_total": _coerce_number(item.get("line_total") if item.get("line_total") is not None else item.get("amount"), 0.0),
        }
        if include_category:
            line_item["category"] = _nullable_string(item.get("category"))
        else:
            line_item["tax_rate"] = _optional_number(item.get("tax_rate"))
        normalized.append(line_item)
    return normalized


def _build_metadata(*, document_id: str, source_file_name: str, page_count: int) -> dict[str, Any]:
    return {
        "document_id": str(document_id),
        "source_file_name": str(source_file_name or "unknown"),
        "page_count": max(int(page_count), 1),
        "processed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _coerce_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip().replace(",", "")
    if raw.startswith("$"):
        raw = raw[1:]
    try:
        return float(raw)
    except ValueError:
        return default


def _optional_number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return _coerce_number(value)


def _coerce_currency(value: Any) -> str:
    raw = str(value or "USD").strip().upper()
    if len(raw) == 3 and raw.isalpha():
        return raw
    return "USD"


def _coerce_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _nullable_string(value: Any) -> str | None:
    text = _coerce_string(value)
    return text if text else None


def _coerce_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    date_patterns = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")
    for pattern in date_patterns:
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _nullable_date(value: Any) -> str | None:
    return _coerce_date(value)


def _today_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _nested_get(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
