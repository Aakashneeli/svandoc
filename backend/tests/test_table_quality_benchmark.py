import json
import unittest
from pathlib import Path

from svandoc_backend.quality_eval import evaluate_extraction_quality
from svandoc_backend.quality_gate import evaluate_quality_gate


class TableQualityBenchmarkTests(unittest.TestCase):
    def test_table_benchmark_passes_regression_gate(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        ground_truth_path = repo_root / "datasets/benchmark/v1/table_ground_truth.json"
        prediction_path = repo_root / "datasets/benchmark/v1/table_ci_predictions.json"

        ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
        predictions = json.loads(prediction_path.read_text(encoding="utf-8"))

        evaluation = evaluate_extraction_quality(
            ground_truth=ground_truth,
            predictions=predictions,
        )
        passed, checks = evaluate_quality_gate(
            evaluation,
            metric_name="f1",
            thresholds={"invoice": 0.95, "receipt": 0.95},
        )

        self.assertTrue(passed)
        self.assertTrue(checks["invoice"]["passed"])
        self.assertTrue(checks["receipt"]["passed"])


if __name__ == "__main__":
    unittest.main()
