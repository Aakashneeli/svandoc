import unittest
from pathlib import Path

from svandoc_backend.pilot_metrics import evaluate_pilot_metrics, load_pilot_sessions


class PilotMetricsTests(unittest.TestCase):
    def test_evaluate_pilot_metrics_computes_completion_and_time_to_value(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        csv_path = repo_root / "datasets" / "pilot" / "v1" / "pilot_sessions.csv"
        sessions = load_pilot_sessions(csv_path)

        result = evaluate_pilot_metrics(sessions)
        summary = result["summary"]

        self.assertEqual(summary["total_sessions"], 6)
        self.assertEqual(summary["completed_sessions"], 5)
        self.assertEqual(summary["completion_rate_percent"], 83.33)
        self.assertEqual(summary["median_time_to_value_seconds"], 410)
        self.assertEqual(summary["average_time_to_value_seconds"], 425.0)


if __name__ == "__main__":
    unittest.main()
