import unittest

from svandoc_backend.validation import validate_normalized_payload


class ValidationRuleTests(unittest.TestCase):
    def test_invoice_validation_flags_total_mismatch(self) -> None:
        payload = {
            "invoice": {"issue_date": "2026-02-15", "due_date": "2026-02-20"},
            "amounts": {"currency": "USD", "subtotal": 100.0, "tax": 10.0, "shipping": 5.0, "discount": 0.0, "total": 80.0},
            "line_items": [],
        }
        warnings = validate_normalized_payload(doc_type="invoice", payload=payload)
        self.assertTrue(any("amounts.total mismatch for invoice" in warning for warning in warnings))

    def test_invoice_validation_flags_invalid_date(self) -> None:
        payload = {
            "invoice": {"issue_date": "15/02/2026", "due_date": None},
            "amounts": {"currency": "USD", "subtotal": 10.0, "tax": 1.0, "shipping": 0.0, "discount": 0.0, "total": 11.0},
            "line_items": [],
        }
        warnings = validate_normalized_payload(doc_type="invoice", payload=payload)
        self.assertTrue(any("invoice.issue_date" in warning for warning in warnings))

    def test_receipt_validation_flags_currency_and_line_item_math(self) -> None:
        payload = {
            "receipt": {"transaction_date": "2026-02-15"},
            "amounts": {"currency": "usd", "subtotal": 10.0, "tax": 1.0, "tip": 2.0, "total": 13.0},
            "line_items": [{"quantity": 2, "unit_price": 3.0, "line_total": 10.0}],
        }
        warnings = validate_normalized_payload(doc_type="receipt", payload=payload)
        self.assertTrue(any("amounts.currency" in warning for warning in warnings))
        self.assertTrue(any("line_items.0.line_total mismatch" in warning for warning in warnings))

    def test_valid_payload_has_no_warnings(self) -> None:
        payload = {
            "invoice": {"issue_date": "2026-02-15", "due_date": "2026-02-20"},
            "amounts": {"currency": "USD", "subtotal": 10.0, "tax": 1.0, "shipping": 2.0, "discount": 0.5, "total": 12.5},
            "line_items": [{"quantity": 2, "unit_price": 5.0, "line_total": 10.0}],
        }
        warnings = validate_normalized_payload(doc_type="invoice", payload=payload)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
