import re
import unittest

from fastapi.testclient import TestClient

from svandoc_backend.main import app


TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class HealthAndReadinessEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def assert_success_envelope(self, payload: dict[str, object]) -> None:
        self.assertEqual(payload["status"], "success")
        self.assertIsInstance(payload["request_id"], str)
        self.assertTrue(payload["request_id"])
        self.assertRegex(str(payload["timestamp"]), TIMESTAMP_PATTERN)
        self.assertIsNone(payload["error"])
        self.assertIsInstance(payload["meta"], dict)
        self.assertEqual(payload["meta"]["api_version"], "v1")
        self.assertIsNotNone(payload["data"])

    def test_health_returns_ok_payload(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assert_success_envelope(payload)
        self.assertEqual(payload["data"]["service"], "svandoc-backend")
        self.assertEqual(payload["data"]["status"], "ok")

    def test_ready_returns_ready_payload(self) -> None:
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assert_success_envelope(payload)
        self.assertEqual(payload["data"]["service"], "svandoc-backend")
        self.assertEqual(payload["data"]["status"], "ready")
        self.assertEqual(payload["data"]["checks"]["api"], "ok")

    def test_request_id_header_is_respected(self) -> None:
        response = self.client.get("/health", headers={"x-request-id": "req_custom_123"})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["request_id"], "req_custom_123")


if __name__ == "__main__":
    unittest.main()
