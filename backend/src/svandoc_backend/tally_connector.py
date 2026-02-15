"""Tally import package builder."""

from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import Any


@dataclass(frozen=True)
class TallyExportPackage:
    filename: str
    content: bytes


def build_tally_import_package(payload: dict[str, Any]) -> TallyExportPackage:
    doc_type = str(payload.get("document_type", "")).strip().lower() or "invoice"
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    reference = _reference(payload, doc_type)
    party = _party(payload, doc_type)

    manifest = {
        "provider": "tally",
        "package_version": "1.0.0",
        "document_id": str(metadata.get("document_id", "")).strip(),
        "document_type": doc_type,
        "reference": reference,
        "currency": str(amounts.get("currency", "")).strip() or "USD",
    }

    voucher_xml = _build_voucher_xml(payload, doc_type=doc_type, reference=reference, party=party)
    summary_csv = _build_summary_csv(payload, doc_type=doc_type, reference=reference, party=party)

    archive_name = f"{str(metadata.get('document_id', '')).strip() or 'document'}.tally.zip"
    archive = BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True))
        package.writestr("voucher.xml", voucher_xml)
        package.writestr("summary.csv", summary_csv)
    return TallyExportPackage(filename=archive_name, content=archive.getvalue())


def _build_voucher_xml(payload: dict[str, Any], *, doc_type: str, reference: str, party: str) -> str:
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    total = _float_or_zero(amounts.get("total"))
    tax = _float_or_zero(amounts.get("tax"))
    currency = str(amounts.get("currency", "")).strip() or "USD"
    escaped_reference = _xml_escape(reference or "UNKNOWN")
    escaped_party = _xml_escape(party or "UNKNOWN")
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<ENVELOPE>\n"
        "  <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>\n"
        "  <BODY>\n"
        "    <IMPORTDATA>\n"
        "      <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>\n"
        "      <REQUESTDATA>\n"
        "        <TALLYMESSAGE>\n"
        f"          <VOUCHER VCHTYPE=\"{_xml_escape(doc_type.title())}\" ACTION=\"Create\">\n"
        f"            <REFERENCE>{escaped_reference}</REFERENCE>\n"
        f"            <PARTYLEDGERNAME>{escaped_party}</PARTYLEDGERNAME>\n"
        f"            <AMOUNT>{total:.2f}</AMOUNT>\n"
        f"            <TAXAMOUNT>{tax:.2f}</TAXAMOUNT>\n"
        f"            <CURRENCY>{_xml_escape(currency)}</CURRENCY>\n"
        "          </VOUCHER>\n"
        "        </TALLYMESSAGE>\n"
        "      </REQUESTDATA>\n"
        "    </IMPORTDATA>\n"
        "  </BODY>\n"
        "</ENVELOPE>\n"
    )


def _build_summary_csv(payload: dict[str, Any], *, doc_type: str, reference: str, party: str) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "document_id",
            "document_type",
            "reference",
            "party",
            "currency",
            "subtotal",
            "tax",
            "total",
        ],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerow(
        {
            "document_id": str(metadata.get("document_id", "")).strip(),
            "document_type": doc_type,
            "reference": reference,
            "party": party,
            "currency": str(amounts.get("currency", "")).strip() or "USD",
            "subtotal": _float_or_zero(amounts.get("subtotal")),
            "tax": _float_or_zero(amounts.get("tax")),
            "total": _float_or_zero(amounts.get("total")),
        }
    )
    return output.getvalue()


def _reference(payload: dict[str, Any], doc_type: str) -> str:
    if doc_type == "receipt":
        receipt = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else {}
        return str(receipt.get("receipt_number", "")).strip()
    invoice = payload.get("invoice") if isinstance(payload.get("invoice"), dict) else {}
    return str(invoice.get("invoice_number", "")).strip()


def _party(payload: dict[str, Any], doc_type: str) -> str:
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


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
