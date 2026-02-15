import json
import unittest

from svandoc_backend.export_service import build_json_export


class ExportServiceTests(unittest.TestCase):
    def test_build_json_export_returns_schema_compatible_payload(self) -> None:
        payload = {
            "schema_version": "1.0.0",
            "document_type": "invoice",
            "metadata": {"document_id": "doc-1", "source_file_name": "invoice.pdf", "page_count": 1},
            "vendor": {"name": "ACME Inc", "tax_id": None, "address": None, "email": None},
            "customer": None,
            "invoice": {
                "invoice_number": "INV-1",
                "issue_date": "2026-02-15",
                "due_date": None,
                "purchase_order_number": None,
            },
            "amounts": {
                "currency": "USD",
                "subtotal": 100.0,
                "tax": 8.75,
                "shipping": None,
                "discount": None,
                "total": 108.75,
            },
            "line_items": [],
            "payment_terms": None,
            "confidence": {"overall": 0.95, "fields": {"amounts.total": 0.97}},
            "raw_text": "INVOICE OCR RAW",
            "review_required": False,
            "warnings": [],
        }

        exported = build_json_export(payload)
        exported_payload = json.loads(exported.decode("utf-8"))
        self.assertEqual(exported_payload["schema_version"], "1.0.0")
        self.assertEqual(exported_payload["document_type"], "invoice")
        self.assertEqual(exported_payload["amounts"]["total"], 108.75)

    def test_build_json_export_raises_for_non_canonical_payload(self) -> None:
        with self.assertRaises(ValueError):
            build_json_export(
                {
                    "schema_version": "1.0.0",
                    "document_type": "invoice",
                    "metadata": {"document_id": "doc-1"},
                }
            )


if __name__ == "__main__":
    unittest.main()
