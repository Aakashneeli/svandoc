import os
import unittest

from fastapi.testclient import TestClient

from svandoc_backend.main import app
from svandoc_backend.metrics import record_job_result, reset_metrics_for_tests


class MetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        os.environ["QUEUE_BACKEND"] = "disabled"
        reset_metrics_for_tests()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend
        reset_metrics_for_tests()

    def test_metrics_endpoint_reports_api_latency_and_error_rate(self) -> None:
        self.client.get("/health")
        self.client.get("/not-found-route")

        metrics_response = self.client.get("/metrics")
        self.assertEqual(metrics_response.status_code, 200)
        payload = metrics_response.json()["data"]

        self.assertGreaterEqual(payload["api"]["requests_total"], 2)
        self.assertGreaterEqual(payload["api"]["errors_total"], 1)
        self.assertGreater(payload["api"]["latency_ms"]["sample_size"], 0)
        self.assertEqual(payload["queue"]["status"], "disabled")
        self.assertEqual(payload["queue"]["depth"], 0)

    def test_metrics_endpoint_reports_job_counters(self) -> None:
        record_job_result("completed")
        record_job_result("review_required")
        record_job_result("failed")

        metrics_response = self.client.get("/metrics")
        self.assertEqual(metrics_response.status_code, 200)
        jobs = metrics_response.json()["data"]["jobs"]
        self.assertEqual(jobs["processed_total"], 3)
        self.assertEqual(jobs["failed_total"], 1)
        self.assertEqual(jobs["review_required_total"], 1)


if __name__ == "__main__":
    unittest.main()
