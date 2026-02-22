import unittest

from svandoc_backend.normalization import normalize_ocr_output


class NormalizationTests(unittest.TestCase):
    def test_normalize_invoice_payload_includes_required_fields(self) -> None:
        payload = normalize_ocr_output(
            doc_type="invoice",
            document_id="doc-1",
            source_file_name="invoice-a.pdf",
            page_count=2,
            raw_text="INVOICE RAW",
            structured_payload={
                "vendor_name": "ACME Inc",
                "invoice_number": "INV-001",
                "issue_date": "2026-02-14",
                "currency": "usd",
                "subtotal": "100.50",
                "tax": "8.25",
                "total": "108.75",
            },
            review_required=False,
        )

        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["document_type"], "invoice")
        self.assertEqual(payload["vendor"]["name"], "ACME Inc")
        self.assertEqual(payload["invoice"]["invoice_number"], "INV-001")
        self.assertEqual(payload["invoice"]["issue_date"], "2026-02-14")
        self.assertEqual(payload["amounts"]["currency"], "USD")
        self.assertEqual(payload["amounts"]["total"], 108.75)
        self.assertIn("confidence", payload)
        self.assertIn("raw_text", payload)
        self.assertIn("review_required", payload)

    def test_normalize_receipt_payload_includes_required_fields(self) -> None:
        payload = normalize_ocr_output(
            doc_type="receipt",
            document_id="doc-2",
            source_file_name="receipt-a.jpg",
            page_count=1,
            raw_text="RECEIPT RAW",
            structured_payload={
                "merchant_name": "Store One",
                "receipt_number": "R-42",
                "transaction_date": "02/14/2026",
                "subtotal": 20.0,
                "tax": 1.2,
                "total": 21.2,
            },
            review_required=True,
        )

        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["document_type"], "receipt")
        self.assertEqual(payload["merchant"]["name"], "Store One")
        self.assertEqual(payload["receipt"]["receipt_number"], "R-42")
        self.assertEqual(payload["receipt"]["transaction_date"], "2026-02-14")
        self.assertEqual(payload["amounts"]["currency"], "USD")
        self.assertEqual(payload["amounts"]["total"], 21.2)
        self.assertTrue(payload["review_required"])

    def test_normalize_invoice_supplies_safe_defaults_for_missing_required_fields(self) -> None:
        payload = normalize_ocr_output(
            doc_type="invoice",
            document_id="doc-3",
            source_file_name="unknown.pdf",
            page_count=0,
            raw_text="",
            structured_payload={},
            review_required=False,
        )

        self.assertEqual(payload["vendor"]["name"], "UNKNOWN_VENDOR")
        self.assertEqual(payload["invoice"]["invoice_number"], "UNKNOWN-INVOICE")
        self.assertEqual(payload["amounts"]["currency"], "USD")
        self.assertEqual(payload["amounts"]["subtotal"], 0.0)
        self.assertEqual(payload["metadata"]["page_count"], 1)

    def test_normalize_invoice_prefers_advanced_table_line_items(self) -> None:
        payload = normalize_ocr_output(
            doc_type="invoice",
            document_id="doc-4",
            source_file_name="invoice-table.pdf",
            page_count=2,
            raw_text="TABLE RAW",
            structured_payload={
                "line_items": [{"description": "placeholder", "quantity": 1, "unit_price": 1, "line_total": 1}],
                "tables": [
                    {
                        "table_id": "line_items",
                        "page_number": 1,
                        "headers": ["Description", "Qty", "Unit Price", "Amount"],
                        "rows": [["Design Work", "2", "50.00", "100.00"]],
                    },
                    {
                        "table_id": "line_items",
                        "page_number": 2,
                        "headers": ["Description", "Qty", "Unit Price", "Amount"],
                        "rows": [["Support", "1", "25.00", "25.00"]],
                    },
                ],
            },
            review_required=False,
        )

        self.assertEqual(len(payload["line_items"]), 2)
        self.assertEqual(payload["line_items"][0]["description"], "Design Work")
        self.assertEqual(payload["line_items"][1]["description"], "Support")
        self.assertEqual(payload["line_items"][1]["line_total"], 25.0)


if __name__ == "__main__":
    unittest.main()
