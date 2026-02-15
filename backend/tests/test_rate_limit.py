import os
import unittest

from fastapi.testclient import TestClient

from svandoc_backend.main import app
from svandoc_backend.rate_limit import rate_limiter


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_env = {
            "RATE_LIMIT_ENABLED": os.environ.get("RATE_LIMIT_ENABLED"),
            "RATE_LIMIT_WINDOW_SECONDS": os.environ.get("RATE_LIMIT_WINDOW_SECONDS"),
            "RATE_LIMIT_MAX_REQUESTS": os.environ.get("RATE_LIMIT_MAX_REQUESTS"),
            "RATE_LIMIT_UPLOAD_MAX_REQUESTS": os.environ.get("RATE_LIMIT_UPLOAD_MAX_REQUESTS"),
            "RATE_LIMIT_BLOCK_SECONDS": os.environ.get("RATE_LIMIT_BLOCK_SECONDS"),
        }
        os.environ["RATE_LIMIT_ENABLED"] = "1"
        os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
        os.environ["RATE_LIMIT_MAX_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_UPLOAD_MAX_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_BLOCK_SECONDS"] = "5"
        rate_limiter.reset_for_tests()
        self.client = TestClient(app)
        self.headers = {"x-user-id": "user-rate-test"}

    def tearDown(self) -> None:
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        rate_limiter.reset_for_tests()

    def test_api_rate_limit_returns_429_after_threshold(self) -> None:
        first = self.client.get("/api/not-real", headers=self.headers)
        second = self.client.get("/api/not-real", headers=self.headers)
        third = self.client.get("/api/not-real", headers=self.headers)

        self.assertEqual(first.status_code, 404)
        self.assertEqual(second.status_code, 404)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.json()["error"]["code"], "RATE_LIMITED")
        self.assertIn("Retry-After", third.headers)

    def test_abuse_guardrail_transitions_to_blocked_state(self) -> None:
        self.client.get("/api/not-real", headers=self.headers)
        self.client.get("/api/not-real", headers=self.headers)
        self.client.get("/api/not-real", headers=self.headers)
        blocked = self.client.get("/api/not-real", headers=self.headers)

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error"]["code"], "ABUSE_BLOCKED")

    def test_non_api_routes_not_rate_limited(self) -> None:
        for _ in range(10):
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
