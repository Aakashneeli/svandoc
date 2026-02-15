import os
import unittest

from fastapi.testclient import TestClient

from svandoc_backend.main import app
from svandoc_backend.metrics import record_api_request, record_job_result, reset_metrics_for_tests


class AlertThresholdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_env = {
            "QUEUE_BACKEND": os.environ.get("QUEUE_BACKEND"),
            "ALERT_FAILED_RECENT_THRESHOLD": os.environ.get("ALERT_FAILED_RECENT_THRESHOLD"),
            "ALERT_QUEUE_BACKLOG_DEPTH": os.environ.get("ALERT_QUEUE_BACKLOG_DEPTH"),
            "ALERT_API_ERROR_RATE_THRESHOLD": os.environ.get("ALERT_API_ERROR_RATE_THRESHOLD"),
        }
        os.environ["QUEUE_BACKEND"] = "disabled"
        os.environ["ALERT_FAILED_RECENT_THRESHOLD"] = "2"
        os.environ["ALERT_QUEUE_BACKLOG_DEPTH"] = "3"
        os.environ["ALERT_API_ERROR_RATE_THRESHOLD"] = "0.25"
        reset_metrics_for_tests()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reset_metrics_for_tests()

    def test_alerts_endpoint_returns_ok_when_thresholds_not_crossed(self) -> None:
        response = self.client.get("/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["active"], [])

    def test_alerts_trigger_for_repeated_failures_and_error_rate(self) -> None:
        record_job_result("failed")
        record_job_result("failed")
        record_api_request(duration_ms=10, status_code=500)
        record_api_request(duration_ms=11, status_code=500)
        record_api_request(duration_ms=12, status_code=200)

        response = self.client.get("/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "alerting")

        codes = {alert["code"] for alert in data["active"]}
        self.assertIn("REPEATED_JOB_FAILURES", codes)
        self.assertIn("API_ERROR_RATE_HIGH", codes)

    def test_metrics_endpoint_embeds_alert_status(self) -> None:
        record_job_result("failed")
        record_job_result("failed")
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        alerts = response.json()["data"]["alerts"]
        self.assertEqual(alerts["status"], "alerting")


if __name__ == "__main__":
    unittest.main()
