"""Sage phased connector strategy helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SageExportPlan:
    phase: str
    storage_uri_hint: str
    payload: dict[str, Any]


def build_sage_export_plan(payload: dict[str, Any]) -> SageExportPlan:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    doc_type = str(payload.get("document_type", "")).strip().lower()
    identity = _identity_section(payload, doc_type)
    party_name = _party_name(payload, doc_type)

    plan_payload: dict[str, Any] = {
        "provider": "sage",
        "strategy_version": "2026-02",
        "phases": [
            {
                "phase": "phase_1_file_exchange",
                "status": "ready",
                "description": "Export structured payload for manual Sage import and finance reconciliation.",
                "deliverables": ["sage_mapping_json", "audit_metadata"],
            },
            {
                "phase": "phase_2_partner_api",
                "status": "planned",
                "description": "Transition to direct API sync using connector credentials per workspace.",
                "deliverables": ["oauth_token_flow", "sync_status_tracking", "idempotent_retries"],
            },
        ],
        "document_summary": {
            "document_id": str(metadata.get("document_id", "")).strip(),
            "document_type": doc_type or "invoice",
            "reference": identity,
            "counterparty": party_name,
            "currency": str(amounts.get("currency", "")).strip() or "USD",
            "total": _float_or_zero(amounts.get("total")),
            "tax": _float_or_zero(amounts.get("tax")),
        },
    }
    return SageExportPlan(
        phase="phase_1_file_exchange",
        storage_uri_hint="sage://phase-1/file-exchange",
        payload=plan_payload,
    )


def _identity_section(payload: dict[str, Any], doc_type: str) -> str:
    if doc_type == "receipt":
        receipt = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else {}
        return str(receipt.get("receipt_number", "")).strip()
    invoice = payload.get("invoice") if isinstance(payload.get("invoice"), dict) else {}
    return str(invoice.get("invoice_number", "")).strip()


def _party_name(payload: dict[str, Any], doc_type: str) -> str:
    if doc_type == "receipt":
        merchant = payload.get("merchant") if isinstance(payload.get("merchant"), dict) else {}
        return str(merchant.get("name", "")).strip()
    vendor = payload.get("vendor") if isinstance(payload.get("vendor"), dict) else {}
    return str(vendor.get("name", "")).strip()


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
