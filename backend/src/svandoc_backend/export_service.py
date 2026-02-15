"""Export generation helpers for canonical extraction payloads."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from io import BytesIO
from typing import Any

from openpyxl import Workbook


def validate_canonical_payload(payload: dict[str, Any]) -> None:
    required_fields = {
        "schema_version",
        "document_type",
        "metadata",
        "amounts",
        "line_items",
        "confidence",
        "raw_text",
        "review_required",
        "warnings",
    }
    missing = sorted(required_fields - set(payload.keys()))
    if missing:
        raise ValueError(f"Canonical payload missing required fields: {', '.join(missing)}")

    doc_type = str(payload.get("document_type", "")).strip().lower()
    if doc_type not in {"invoice", "receipt"}:
        raise ValueError("Canonical payload has unsupported document_type.")

    if doc_type == "invoice":
        if "vendor" not in payload or "invoice" not in payload:
            raise ValueError("Invoice payload requires both 'vendor' and 'invoice' sections.")
    if doc_type == "receipt":
        if "merchant" not in payload or "receipt" not in payload:
            raise ValueError("Receipt payload requires both 'merchant' and 'receipt' sections.")


def build_json_export(payload: dict[str, Any]) -> bytes:
    validate_canonical_payload(payload)
    # Stable key order keeps exports deterministic for downstream comparison and testing.
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
    return rendered.encode("utf-8")


def build_csv_export(payload: dict[str, Any]) -> bytes:
    validate_canonical_payload(payload)
    doc_type = str(payload.get("document_type", "")).strip().lower()
    headers = _invoice_csv_headers() if doc_type == "invoice" else _receipt_csv_headers()
    row = _build_invoice_csv_row(payload) if doc_type == "invoice" else _build_receipt_csv_row(payload)

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def build_xlsx_export(payload: dict[str, Any]) -> bytes:
    validate_canonical_payload(payload)
    doc_type = str(payload.get("document_type", "")).strip().lower()
    headers = _invoice_csv_headers() if doc_type == "invoice" else _receipt_csv_headers()
    typed_row = _build_invoice_xlsx_row(payload) if doc_type == "invoice" else _build_receipt_xlsx_row(payload)

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "summary"
    summary_sheet.append(headers)
    summary_sheet.append([typed_row.get(header) for header in headers])

    line_items_sheet = workbook.create_sheet(title="line_items")
    line_items_sheet.append(["index", "json"])
    line_items = payload.get("line_items")
    if isinstance(line_items, list):
        for index, item in enumerate(line_items):
            line_items_sheet.append([index, _to_csv_json(item)])

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _invoice_csv_headers() -> list[str]:
    return [
        "document_id",
        "source_file_name",
        "page_count",
        "schema_version",
        "document_type",
        "vendor_name",
        "vendor_tax_id",
        "vendor_address",
        "vendor_email",
        "customer_name",
        "customer_address",
        "invoice_number",
        "issue_date",
        "due_date",
        "purchase_order_number",
        "currency",
        "subtotal",
        "tax",
        "shipping",
        "discount",
        "total",
        "payment_terms",
        "review_required",
        "warning_count",
        "line_item_count",
        "line_items_json",
        "confidence_overall",
    ]


def _receipt_csv_headers() -> list[str]:
    return [
        "document_id",
        "source_file_name",
        "page_count",
        "schema_version",
        "document_type",
        "merchant_name",
        "merchant_tax_id",
        "merchant_address",
        "merchant_phone",
        "receipt_number",
        "transaction_date",
        "transaction_time",
        "payment_method",
        "currency",
        "subtotal",
        "tax",
        "tip",
        "total",
        "review_required",
        "warning_count",
        "line_item_count",
        "line_items_json",
        "confidence_overall",
    ]


def _build_invoice_csv_row(payload: dict[str, Any]) -> dict[str, str]:
    metadata = _dict_value(payload, "metadata")
    vendor = _dict_value(payload, "vendor")
    customer = _dict_value(payload, "customer")
    invoice = _dict_value(payload, "invoice")
    amounts = _dict_value(payload, "amounts")
    confidence = _dict_value(payload, "confidence")
    warnings = payload.get("warnings")
    line_items = payload.get("line_items")

    return {
        "document_id": _to_csv_scalar(metadata.get("document_id")),
        "source_file_name": _to_csv_scalar(metadata.get("source_file_name")),
        "page_count": _to_csv_scalar(metadata.get("page_count")),
        "schema_version": _to_csv_scalar(payload.get("schema_version")),
        "document_type": _to_csv_scalar(payload.get("document_type")),
        "vendor_name": _to_csv_scalar(vendor.get("name")),
        "vendor_tax_id": _to_csv_scalar(vendor.get("tax_id")),
        "vendor_address": _to_csv_scalar(vendor.get("address")),
        "vendor_email": _to_csv_scalar(vendor.get("email")),
        "customer_name": _to_csv_scalar(customer.get("name")),
        "customer_address": _to_csv_scalar(customer.get("address")),
        "invoice_number": _to_csv_scalar(invoice.get("invoice_number")),
        "issue_date": _to_csv_scalar(invoice.get("issue_date")),
        "due_date": _to_csv_scalar(invoice.get("due_date")),
        "purchase_order_number": _to_csv_scalar(invoice.get("purchase_order_number")),
        "currency": _to_csv_scalar(amounts.get("currency")),
        "subtotal": _to_csv_scalar(amounts.get("subtotal")),
        "tax": _to_csv_scalar(amounts.get("tax")),
        "shipping": _to_csv_scalar(amounts.get("shipping")),
        "discount": _to_csv_scalar(amounts.get("discount")),
        "total": _to_csv_scalar(amounts.get("total")),
        "payment_terms": _to_csv_scalar(payload.get("payment_terms")),
        "review_required": _to_csv_scalar(payload.get("review_required")),
        "warning_count": _to_csv_scalar(len(warnings) if isinstance(warnings, list) else 0),
        "line_item_count": _to_csv_scalar(len(line_items) if isinstance(line_items, list) else 0),
        "line_items_json": _to_csv_json(line_items if isinstance(line_items, list) else []),
        "confidence_overall": _to_csv_scalar(confidence.get("overall")),
    }


def _build_receipt_csv_row(payload: dict[str, Any]) -> dict[str, str]:
    metadata = _dict_value(payload, "metadata")
    merchant = _dict_value(payload, "merchant")
    receipt = _dict_value(payload, "receipt")
    amounts = _dict_value(payload, "amounts")
    confidence = _dict_value(payload, "confidence")
    warnings = payload.get("warnings")
    line_items = payload.get("line_items")

    return {
        "document_id": _to_csv_scalar(metadata.get("document_id")),
        "source_file_name": _to_csv_scalar(metadata.get("source_file_name")),
        "page_count": _to_csv_scalar(metadata.get("page_count")),
        "schema_version": _to_csv_scalar(payload.get("schema_version")),
        "document_type": _to_csv_scalar(payload.get("document_type")),
        "merchant_name": _to_csv_scalar(merchant.get("name")),
        "merchant_tax_id": _to_csv_scalar(merchant.get("tax_id")),
        "merchant_address": _to_csv_scalar(merchant.get("address")),
        "merchant_phone": _to_csv_scalar(merchant.get("phone")),
        "receipt_number": _to_csv_scalar(receipt.get("receipt_number")),
        "transaction_date": _to_csv_scalar(receipt.get("transaction_date")),
        "transaction_time": _to_csv_scalar(receipt.get("transaction_time")),
        "payment_method": _to_csv_scalar(receipt.get("payment_method")),
        "currency": _to_csv_scalar(amounts.get("currency")),
        "subtotal": _to_csv_scalar(amounts.get("subtotal")),
        "tax": _to_csv_scalar(amounts.get("tax")),
        "tip": _to_csv_scalar(amounts.get("tip")),
        "total": _to_csv_scalar(amounts.get("total")),
        "review_required": _to_csv_scalar(payload.get("review_required")),
        "warning_count": _to_csv_scalar(len(warnings) if isinstance(warnings, list) else 0),
        "line_item_count": _to_csv_scalar(len(line_items) if isinstance(line_items, list) else 0),
        "line_items_json": _to_csv_json(line_items if isinstance(line_items, list) else []),
        "confidence_overall": _to_csv_scalar(confidence.get("overall")),
    }


def _build_invoice_xlsx_row(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = _dict_value(payload, "metadata")
    vendor = _dict_value(payload, "vendor")
    customer = _dict_value(payload, "customer")
    invoice = _dict_value(payload, "invoice")
    amounts = _dict_value(payload, "amounts")
    confidence = _dict_value(payload, "confidence")
    warnings = payload.get("warnings")
    line_items = payload.get("line_items")

    return {
        "document_id": metadata.get("document_id"),
        "source_file_name": metadata.get("source_file_name"),
        "page_count": _typed_int(metadata.get("page_count")),
        "schema_version": payload.get("schema_version"),
        "document_type": payload.get("document_type"),
        "vendor_name": vendor.get("name"),
        "vendor_tax_id": vendor.get("tax_id"),
        "vendor_address": vendor.get("address"),
        "vendor_email": vendor.get("email"),
        "customer_name": customer.get("name"),
        "customer_address": customer.get("address"),
        "invoice_number": invoice.get("invoice_number"),
        "issue_date": _typed_date(invoice.get("issue_date")),
        "due_date": _typed_date(invoice.get("due_date")),
        "purchase_order_number": invoice.get("purchase_order_number"),
        "currency": amounts.get("currency"),
        "subtotal": _typed_float(amounts.get("subtotal")),
        "tax": _typed_float(amounts.get("tax")),
        "shipping": _typed_optional_float(amounts.get("shipping")),
        "discount": _typed_optional_float(amounts.get("discount")),
        "total": _typed_float(amounts.get("total")),
        "payment_terms": payload.get("payment_terms"),
        "review_required": bool(payload.get("review_required", False)),
        "warning_count": len(warnings) if isinstance(warnings, list) else 0,
        "line_item_count": len(line_items) if isinstance(line_items, list) else 0,
        "line_items_json": _to_csv_json(line_items if isinstance(line_items, list) else []),
        "confidence_overall": _typed_float(confidence.get("overall")),
    }


def _build_receipt_xlsx_row(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = _dict_value(payload, "metadata")
    merchant = _dict_value(payload, "merchant")
    receipt = _dict_value(payload, "receipt")
    amounts = _dict_value(payload, "amounts")
    confidence = _dict_value(payload, "confidence")
    warnings = payload.get("warnings")
    line_items = payload.get("line_items")

    return {
        "document_id": metadata.get("document_id"),
        "source_file_name": metadata.get("source_file_name"),
        "page_count": _typed_int(metadata.get("page_count")),
        "schema_version": payload.get("schema_version"),
        "document_type": payload.get("document_type"),
        "merchant_name": merchant.get("name"),
        "merchant_tax_id": merchant.get("tax_id"),
        "merchant_address": merchant.get("address"),
        "merchant_phone": merchant.get("phone"),
        "receipt_number": receipt.get("receipt_number"),
        "transaction_date": _typed_date(receipt.get("transaction_date")),
        "transaction_time": receipt.get("transaction_time"),
        "payment_method": receipt.get("payment_method"),
        "currency": amounts.get("currency"),
        "subtotal": _typed_float(amounts.get("subtotal")),
        "tax": _typed_float(amounts.get("tax")),
        "tip": _typed_optional_float(amounts.get("tip")),
        "total": _typed_float(amounts.get("total")),
        "review_required": bool(payload.get("review_required", False)),
        "warning_count": len(warnings) if isinstance(warnings, list) else 0,
        "line_item_count": len(line_items) if isinstance(line_items, list) else 0,
        "line_items_json": _to_csv_json(line_items if isinstance(line_items, list) else []),
        "confidence_overall": _typed_float(confidence.get("overall")),
    }


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _to_csv_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _to_csv_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)


def _typed_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _typed_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return _typed_float(value)


def _typed_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _typed_date(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed
