import unittest

from svandoc_backend.sage_connector import build_sage_export_plan


class SageConnectorTests(unittest.TestCase):
    def test_build_sage_export_plan_for_invoice(self) -> None:
        plan = build_sage_export_plan(
            {
                "document_type": "invoice",
                "metadata": {"document_id": "doc-1"},
                "vendor": {"name": "ACME"},
                "invoice": {"invoice_number": "INV-100"},
                "amounts": {"currency": "USD", "total": 120.5, "tax": 10.5},
            }
        )
        self.assertEqual(plan.phase, "phase_1_file_exchange")
        self.assertEqual(plan.payload["provider"], "sage")
        self.assertEqual(plan.payload["document_summary"]["reference"], "INV-100")
        self.assertEqual(plan.payload["document_summary"]["counterparty"], "ACME")


if __name__ == "__main__":
    unittest.main()
