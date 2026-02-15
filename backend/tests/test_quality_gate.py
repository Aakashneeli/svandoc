import unittest

from svandoc_backend.quality_gate import evaluate_quality_gate


class QualityGateTests(unittest.TestCase):
    def test_quality_gate_passes_when_invoice_and_receipt_meet_thresholds(self) -> None:
        quality_eval = {
            "by_doc_type": {
                "invoice": {"overall": {"f1": 0.93}},
                "receipt": {"overall": {"f1": 0.89}},
            }
        }
        passed, checks = evaluate_quality_gate(
            quality_eval,
            metric_name="f1",
            thresholds={"invoice": 0.92, "receipt": 0.88},
        )

        self.assertTrue(passed)
        self.assertTrue(checks["invoice"]["passed"])
        self.assertTrue(checks["receipt"]["passed"])

    def test_quality_gate_fails_when_any_doc_type_drops_below_threshold(self) -> None:
        quality_eval = {
            "by_doc_type": {
                "invoice": {"overall": {"f1": 0.91}},
                "receipt": {"overall": {"f1": 0.90}},
            }
        }
        passed, checks = evaluate_quality_gate(
            quality_eval,
            metric_name="f1",
            thresholds={"invoice": 0.92, "receipt": 0.88},
        )

        self.assertFalse(passed)
        self.assertFalse(checks["invoice"]["passed"])
        self.assertEqual(checks["invoice"]["reason"], "below_threshold")
        self.assertTrue(checks["receipt"]["passed"])

    def test_quality_gate_fails_when_metric_is_missing(self) -> None:
        quality_eval = {
            "by_doc_type": {
                "invoice": {"overall": {"precision": 0.95}},
                "receipt": {"overall": {"f1": 0.90}},
            }
        }
        passed, checks = evaluate_quality_gate(
            quality_eval,
            metric_name="f1",
            thresholds={"invoice": 0.92, "receipt": 0.88},
        )

        self.assertFalse(passed)
        self.assertFalse(checks["invoice"]["passed"])
        self.assertEqual(checks["invoice"]["reason"], "missing_metric")


if __name__ == "__main__":
    unittest.main()
