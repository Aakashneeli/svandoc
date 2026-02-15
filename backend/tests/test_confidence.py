import unittest

from svandoc_backend.confidence import build_field_confidence_map


class ConfidenceMapTests(unittest.TestCase):
    def test_invoice_confidence_map_covers_extractable_fields(self) -> None:
        normalized_invoice = {
            "vendor": {"name": "ACME", "tax_id": None, "address": None, "email": None},
            "customer": {"name": "Globex", "address": None},
            "invoice": {
                "invoice_number": "INV-1",
                "issue_date": "2026-02-15",
                "due_date": None,
                "purchase_order_number": None,
            },
            "amounts": {"currency": "USD", "subtotal": 10.0, "tax": 1.0, "shipping": None, "discount": None, "total": 11.0},
            "line_items": [{"description": "A", "quantity": 1.0, "unit_price": 10.0, "line_total": 10.0, "tax_rate": None}],
            "payment_terms": None,
        }
        raw_confidence = {
            "vendor_name": 0.95,
            "invoice_number": 0.9,
            "issue_date": 0.92,
            "subtotal": 0.88,
            "tax": 0.89,
            "total": 0.93,
            "line_items": [{"description": 0.85, "quantity": 0.86, "unit_price": 0.84, "line_total": 0.83, "tax_rate": 0.8}],
        }

        confidence = build_field_confidence_map(
            doc_type="invoice",
            normalized_payload=normalized_invoice,
            raw_confidence_map=raw_confidence,
        )

        fields = confidence["fields"]
        self.assertIn("vendor.name", fields)
        self.assertIn("invoice.invoice_number", fields)
        self.assertIn("amounts.total", fields)
        self.assertIn("line_items.0.description", fields)
        self.assertIn("payment_terms", fields)
        self.assertEqual(fields["vendor.name"], 0.95)
        self.assertEqual(fields["payment_terms"], 0.0)
        self.assertGreater(confidence["overall"], 0.0)

    def test_receipt_confidence_map_defaults_missing_fields_to_zero(self) -> None:
        normalized_receipt = {
            "merchant": {"name": "Store", "tax_id": None, "address": None, "phone": None},
            "receipt": {"receipt_number": "R-1", "transaction_date": "2026-02-15", "transaction_time": None, "payment_method": None},
            "amounts": {"currency": "USD", "subtotal": 20.0, "tax": 2.0, "tip": None, "total": 22.0},
            "line_items": [],
        }

        confidence = build_field_confidence_map(
            doc_type="receipt",
            normalized_payload=normalized_receipt,
            raw_confidence_map={},
        )

        self.assertEqual(confidence["fields"]["merchant.name"], 0.0)
        self.assertEqual(confidence["fields"]["amounts.total"], 0.0)
        self.assertEqual(confidence["overall"], 0.0)


if __name__ == "__main__":
    unittest.main()
