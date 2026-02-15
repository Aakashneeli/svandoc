import unittest
from types import SimpleNamespace
from unittest.mock import patch

from svandoc_backend.quickbooks_connector import (
    QuickBooksConnectorError,
    build_quickbooks_payload,
    export_to_quickbooks,
)


class QuickBooksConnectorTests(unittest.TestCase):
    def test_build_quickbooks_payload_maps_invoice_fields(self) -> None:
        payload = {
            "document_type": "invoice",
            "metadata": {"document_id": "doc-1"},
            "vendor": {"name": "ACME Supplies"},
            "invoice": {"invoice_number": "INV-123", "issue_date": "2026-02-15"},
            "amounts": {"currency": "USD", "tax": 5.0, "total": 105.0},
            "line_items": [{"description": "Service", "line_total": 105.0}],
        }
        mapped = build_quickbooks_payload(payload)
        self.assertEqual(mapped["DocNumber"], "INV-123")
        self.assertEqual(mapped["VendorRef"]["name"], "ACME Supplies")
        self.assertEqual(mapped["CurrencyRef"]["value"], "USD")
        self.assertEqual(mapped["TxnTaxDetail"]["TotalTax"], 5.0)
        self.assertEqual(mapped["TotalAmt"], 105.0)
        self.assertEqual(mapped["Line"][0]["Amount"], 105.0)

    def test_export_to_quickbooks_returns_connector_uri(self) -> None:
        with patch("httpx.Client.post") as mocked_post:
            mocked_post.return_value = SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"Purchase": {"Id": "qb-purchase-1"}},
            )
            result = export_to_quickbooks(
                access_token="token-1",
                realm_id="realm-123",
                payload={
                    "document_type": "receipt",
                    "metadata": {"document_id": "doc-2"},
                    "merchant": {"name": "Coffee Shop"},
                    "receipt": {"receipt_number": "R-10", "transaction_date": "2026-02-15"},
                    "amounts": {"currency": "USD", "tax": 1.0, "total": 11.0},
                    "line_items": [{"description": "Coffee", "line_total": 11.0}],
                },
            )
        self.assertEqual(result.storage_uri, "quickbooks://realm-123/qb-purchase-1")

    def test_export_to_quickbooks_raises_on_missing_purchase_id(self) -> None:
        with patch("httpx.Client.post") as mocked_post:
            mocked_post.return_value = SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"Purchase": {}},
            )
            with self.assertRaises(QuickBooksConnectorError):
                export_to_quickbooks(
                    access_token="token-1",
                    realm_id="realm-123",
                    payload={
                        "document_type": "invoice",
                        "metadata": {"document_id": "doc-1"},
                        "vendor": {"name": "Vendor"},
                        "invoice": {"invoice_number": "INV-1", "issue_date": "2026-02-15"},
                        "amounts": {"currency": "USD", "tax": 0.0, "total": 10.0},
                        "line_items": [],
                    },
                )


if __name__ == "__main__":
    unittest.main()
