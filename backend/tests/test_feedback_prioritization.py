import unittest
from pathlib import Path

from svandoc_backend.feedback_prioritization import load_feedback_items, prioritize_feedback


class FeedbackPrioritizationTests(unittest.TestCase):
    def test_prioritization_ranks_by_priority_score_then_impact_effort(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        input_path = repo_root / "datasets" / "pilot" / "v1" / "feedback_items.json"
        items = load_feedback_items(input_path)

        ranked = prioritize_feedback(items)
        self.assertGreater(len(ranked), 0)
        self.assertEqual(ranked[0]["id"], "FB-001")
        self.assertGreaterEqual(ranked[0]["priority_score"], ranked[1]["priority_score"])


if __name__ == "__main__":
    unittest.main()

