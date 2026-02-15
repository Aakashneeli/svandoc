"""Export generation helpers for canonical extraction payloads."""

from __future__ import annotations

import json
from typing import Any


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
