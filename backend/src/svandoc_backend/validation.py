"""Validation rules for normalized extraction payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def validate_normalized_payload(*, doc_type: str, payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    warnings.extend(_validate_dates(doc_type=doc_type, payload=payload))
    warnings.extend(_validate_currency(payload=payload))
    warnings.extend(_validate_total_math(doc_type=doc_type, payload=payload))
    warnings.extend(_validate_line_item_math(payload=payload))
    return warnings


def _validate_dates(*, doc_type: str, payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if doc_type == "receipt":
        receipt = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else {}
        transaction_date = receipt.get("transaction_date")
        if not _is_iso_date(transaction_date):
            warnings.append(
                "receipt.transaction_date must be in YYYY-MM-DD format; verify OCR date extraction and correct the value."
            )
        return warnings

    invoice = payload.get("invoice") if isinstance(payload.get("invoice"), dict) else {}
    issue_date = invoice.get("issue_date")
    due_date = invoice.get("due_date")
    if not _is_iso_date(issue_date):
        warnings.append("invoice.issue_date must be in YYYY-MM-DD format; verify OCR date extraction and correct the value.")
    if due_date is not None and not _is_iso_date(due_date):
        warnings.append("invoice.due_date must be in YYYY-MM-DD format; verify OCR date extraction and correct the value.")
    return warnings


def _validate_currency(*, payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    currency = str(amounts.get("currency", "") or "").strip()
    if len(currency) != 3 or not currency.isalpha() or currency.upper() != currency:
        warnings.append(
            "amounts.currency must be a 3-letter uppercase ISO code (for example USD); verify currency detection."
        )
    return warnings


def _validate_total_math(*, doc_type: str, payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    subtotal = _as_number(amounts.get("subtotal"))
    tax = _as_number(amounts.get("tax"))
    total = _as_number(amounts.get("total"))

    if doc_type == "receipt":
        tip = _as_number(amounts.get("tip"))
        expected_total = subtotal + tax + tip
        if abs(expected_total - total) > 0.01:
            warnings.append(
                f"amounts.total mismatch for receipt: expected {expected_total:.2f} (= subtotal + tax + tip), got {total:.2f}."
            )
        return warnings

    shipping = _as_number(amounts.get("shipping"))
    discount = _as_number(amounts.get("discount"))
    expected_total = subtotal + tax + shipping - discount
    if abs(expected_total - total) > 0.01:
        warnings.append(
            f"amounts.total mismatch for invoice: expected {expected_total:.2f} (= subtotal + tax + shipping - discount), got {total:.2f}."
        )
    return warnings


def _validate_line_item_math(*, payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    line_items = payload.get("line_items")
    if not isinstance(line_items, list):
        return warnings
    for idx, item in enumerate(line_items):
        if not isinstance(item, dict):
            continue
        quantity = _as_number(item.get("quantity"))
        unit_price = _as_number(item.get("unit_price"))
        line_total = _as_number(item.get("line_total"))
        expected = quantity * unit_price
        if abs(expected - line_total) > 0.01:
            warnings.append(
                f"line_items.{idx}.line_total mismatch: expected {expected:.2f} (= quantity * unit_price), got {line_total:.2f}."
            )
    return warnings


def _is_iso_date(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%d") == text


def _as_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return 0.0
