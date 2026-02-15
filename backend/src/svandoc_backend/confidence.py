"""Field-level confidence scoring helpers."""

from __future__ import annotations

from typing import Any


def build_field_confidence_map(
    *,
    doc_type: str,
    normalized_payload: dict[str, Any],
    raw_confidence_map: dict[str, Any],
) -> dict[str, Any]:
    field_paths = _collect_field_paths(doc_type=doc_type, payload=normalized_payload)
    fields: dict[str, float] = {}
    for path in field_paths:
        value = _confidence_for_path(path=path, raw_confidence_map=raw_confidence_map)
        fields[path] = value

    overall = 0.0
    if fields:
        overall = sum(fields.values()) / len(fields)

    return {"overall": round(overall, 4), "fields": fields}


def _collect_field_paths(*, doc_type: str, payload: dict[str, Any]) -> list[str]:
    root_sections = ["amounts", "line_items"]
    if doc_type == "receipt":
        root_sections = ["merchant", "receipt", "amounts", "line_items"]
    else:
        root_sections = ["vendor", "customer", "invoice", "amounts", "line_items", "payment_terms"]

    paths: list[str] = []
    for section in root_sections:
        if section in payload:
            _collect_scalar_paths(payload[section], prefix=section, output=paths)
    return paths


def _collect_scalar_paths(value: Any, *, prefix: str, output: list[str]) -> None:
    if isinstance(value, dict):
        for key in value:
            _collect_scalar_paths(value[key], prefix=f"{prefix}.{key}", output=output)
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _collect_scalar_paths(item, prefix=f"{prefix}.{idx}", output=output)
        return
    output.append(prefix)


def _confidence_for_path(*, path: str, raw_confidence_map: dict[str, Any]) -> float:
    canonical_value = _lookup_nested(raw_confidence_map, path)
    if canonical_value is not None:
        return _clamp_confidence(canonical_value)

    alias_value = _lookup_alias(raw_confidence_map=raw_confidence_map, path=path)
    if alias_value is not None:
        return _clamp_confidence(alias_value)

    return 0.0


def _lookup_nested(raw_confidence_map: dict[str, Any], path: str) -> Any:
    current: Any = raw_confidence_map
    for token in path.split("."):
        if isinstance(current, dict):
            current = current.get(token)
            continue
        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def _lookup_alias(*, raw_confidence_map: dict[str, Any], path: str) -> Any:
    aliases = {
        "vendor.name": "vendor_name",
        "vendor.tax_id": "vendor_tax_id",
        "vendor.address": "vendor_address",
        "vendor.email": "vendor_email",
        "customer.name": "customer_name",
        "customer.address": "customer_address",
        "merchant.name": "merchant_name",
        "merchant.tax_id": "merchant_tax_id",
        "merchant.address": "merchant_address",
        "merchant.phone": "merchant_phone",
        "invoice.invoice_number": "invoice_number",
        "invoice.issue_date": "issue_date",
        "invoice.due_date": "due_date",
        "invoice.purchase_order_number": "purchase_order_number",
        "receipt.receipt_number": "receipt_number",
        "receipt.transaction_date": "transaction_date",
        "receipt.transaction_time": "transaction_time",
        "receipt.payment_method": "payment_method",
        "amounts.currency": "currency",
        "amounts.subtotal": "subtotal",
        "amounts.tax": "tax",
        "amounts.shipping": "shipping",
        "amounts.discount": "discount",
        "amounts.tip": "tip",
        "amounts.total": "total",
        "payment_terms": "payment_terms",
    }
    alias_key = aliases.get(path)
    if alias_key is None:
        return None
    return raw_confidence_map.get(alias_key)


def _clamp_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return round(parsed, 4)
