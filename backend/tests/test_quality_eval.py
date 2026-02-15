import unittest

from svandoc_backend.quality_eval import evaluate_extraction_quality


class QualityEvaluationTests(unittest.TestCase):
    def test_evaluation_outputs_precision_recall_by_field_and_doc_type(self) -> None:
        ground_truth = {
            "version": "v1",
            "samples": [
                {
                    "sample_id": "invoice_a",
                    "doc_type": "invoice",
                    "fields": {"vendor.name": "ACME", "amounts.total": 1085.0},
                },
                {
                    "sample_id": "receipt_a",
                    "doc_type": "receipt",
                    "fields": {"merchant.name": "Corner Market", "amounts.total": 17.44},
                },
            ],
        }
        predictions = {
            "version": "pred-v1",
            "samples": [
                {
                    "sample_id": "invoice_a",
                    "doc_type": "invoice",
                    "fields": {"vendor.name": "ACME", "amounts.total": 999.0},
                },
                {
                    "sample_id": "receipt_a",
                    "doc_type": "receipt",
                    "fields": {"merchant.name": "Corner Market", "amounts.total": 17.44, "extra.field": "x"},
                },
            ],
        }

        result = evaluate_extraction_quality(ground_truth=ground_truth, predictions=predictions)
        invoice = result["by_doc_type"]["invoice"]["overall"]
        receipt = result["by_doc_type"]["receipt"]["overall"]

        self.assertEqual(invoice["tp"], 1)
        self.assertEqual(invoice["fp"], 1)
        self.assertEqual(invoice["fn"], 1)
        self.assertEqual(invoice["precision"], 0.5)
        self.assertEqual(invoice["recall"], 0.5)

        self.assertEqual(receipt["tp"], 2)
        self.assertEqual(receipt["fp"], 1)
        self.assertEqual(receipt["fn"], 0)
        self.assertEqual(receipt["precision"], 0.6667)
        self.assertEqual(receipt["recall"], 1.0)

    def test_evaluation_accepts_structured_payload_records(self) -> None:
        ground_truth = {
            "version": "v1",
            "samples": [
                {
                    "sample_id": "invoice_payload",
                    "doc_type": "invoice",
                    "structured_payload": {
                        "vendor": {"name": "ACME"},
                        "amounts": {"total": 1085.0},
                    },
                }
            ],
        }
        predictions = {
            "version": "pred-v1",
            "samples": [
                {
                    "sample_id": "invoice_payload",
                    "doc_type": "invoice",
                    "structured_payload": {
                        "vendor": {"name": "ACME"},
                        "amounts": {"total": 1085.0},
                    },
                }
            ],
        }

        result = evaluate_extraction_quality(ground_truth=ground_truth, predictions=predictions)
        invoice_fields = result["by_doc_type"]["invoice"]["fields"]
        self.assertIn("vendor.name", invoice_fields)
        self.assertIn("amounts.total", invoice_fields)
        self.assertEqual(invoice_fields["vendor.name"]["precision"], 1.0)
        self.assertEqual(invoice_fields["amounts.total"]["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
