import unittest
from types import SimpleNamespace
from unittest.mock import patch

from svandoc_backend.xero_connector import (
    XeroConnectorError,
    build_xero_payload,
    export_to_xero,
)


class XeroConnectorTests(unittest.TestCase):
    def test_build_xero_payload_maps_reference_tax_and_total(self) -> None:
        payload = {
            "document_type": "invoice",
            "metadata": {"document_id": "doc-1"},
            "vendor": {"name": "Vendor A"},
            "invoice": {"invoice_number": "INV-1", "issue_date": "2026-02-15"},
            "amounts": {"currency": "USD", "tax": 2.5, "total": 12.5},
            "line_items": [{"description": "Line", "quantity": 1, "unit_price": 12.5, "line_total": 12.5}],
        }
        mapped = build_xero_payload(payload)
        self.assertEqual(mapped["Reference"], "INV-1")
        self.assertEqual(mapped["Contact"]["Name"], "Vendor A")
        self.assertEqual(mapped["TotalTax"], 2.5)
        self.assertEqual(mapped["LineItems"][0]["LineAmount"], 12.5)

    def test_export_to_xero_retries_then_succeeds(self) -> None:
        retry_response = SimpleNamespace(status_code=429)
        success_response = SimpleNamespace(
            status_code=200,
            json=lambda: {"Invoices": [{"InvoiceID": "xero-invoice-1"}]},
        )
        with patch("httpx.Client.post", side_effect=[retry_response, success_response]):
            result = export_to_xero(
                access_token="token",
                tenant_id="tenant-1",
                payload={
                    "document_type": "receipt",
                    "metadata": {"document_id": "doc-2"},
                    "merchant": {"name": "Shop"},
                    "receipt": {"receipt_number": "R-2", "transaction_date": "2026-02-15"},
                    "amounts": {"currency": "USD", "tax": 1.0, "total": 11.0},
                    "line_items": [],
                },
                idempotency_key="idem-1",
                retry_backoff_seconds=0.001,
            )
        self.assertEqual(result.storage_uri, "xero://tenant-1/xero-invoice-1")
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[0].sync_status, "retrying")
        self.assertEqual(result.attempts[1].sync_status, "synced")

    def test_export_to_xero_fails_after_non_retryable_status(self) -> None:
        with patch("httpx.Client.post", return_value=SimpleNamespace(status_code=400)):
            with self.assertRaises(XeroConnectorError) as context:
                export_to_xero(
                    access_token="token",
                    tenant_id="tenant-1",
                    payload={
                        "document_type": "invoice",
                        "metadata": {"document_id": "doc-3"},
                        "vendor": {"name": "Vendor"},
                        "invoice": {"invoice_number": "INV-3", "issue_date": "2026-02-15"},
                        "amounts": {"currency": "USD", "tax": 0.0, "total": 10.0},
                        "line_items": [],
                    },
                    idempotency_key="idem-2",
                )
        attempts = context.exception.attempts
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].sync_status, "failed")
        self.assertEqual(attempts[0].status_code, 400)


if __name__ == "__main__":
    unittest.main()
