import unittest
from collections import deque
from typing import Any

import httpx

from svandoc_backend.inference_smoke import InferenceTarget, run_inference_smoke


class _StubClient:
    def __init__(self, responses: list[Any], timeout: float = 20.0) -> None:
        self._responses = deque(responses)
        self.timeout = timeout
        self.calls: list[tuple[str, str]] = []

    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return None

    def get(self, url: str, headers: dict[str, str], timeout: float) -> httpx.Response:
        self.calls.append(("GET", url))
        item = self._responses.popleft()
        if isinstance(item, Exception):
            raise item
        return item

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any], timeout: float) -> httpx.Response:
        self.calls.append(("POST", url))
        item = self._responses.popleft()
        if isinstance(item, Exception):
            raise item
        return item


def _response(status_code: int, payload: dict[str, Any], url: str) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(status_code=status_code, request=request, json=payload)


class InferenceSmokeTests(unittest.TestCase):
    def test_run_inference_smoke_success_for_both_targets(self) -> None:
        targets = [
            InferenceTarget(role="primary", base_url="http://localhost:11434/v1", model_name="FL33TW00D-HF/dots.ocr"),
            InferenceTarget(role="fallback", base_url="http://localhost:11435/v1", model_name="datalab-to/chandra"),
        ]
        responses = [
            _response(
                200,
                {"data": [{"id": "FL33TW00D-HF/dots.ocr"}]},
                "http://localhost:11434/v1/models",
            ),
            _response(
                200,
                {"choices": [{"message": {"content": "{\"status\":\"ok\"}"}}]},
                "http://localhost:11434/v1/chat/completions",
            ),
            _response(
                200,
                {"data": [{"id": "datalab-to/chandra"}]},
                "http://localhost:11435/v1/models",
            ),
            _response(
                200,
                {"choices": [{"message": {"content": "{\"status\":\"ok\"}"}}]},
                "http://localhost:11435/v1/chat/completions",
            ),
        ]
        client = _StubClient(responses)
        evidence = run_inference_smoke(targets=targets, client_factory=lambda **_: client)

        self.assertTrue(evidence["overall_success"])
        self.assertEqual(len(evidence["checks"]), 2)
        self.assertTrue(all(item["models_endpoint_ok"] for item in evidence["checks"]))
        self.assertTrue(all(item["completion_ok"] for item in evidence["checks"]))

    def test_run_inference_smoke_reports_failure_when_completion_fails(self) -> None:
        targets = [InferenceTarget(role="primary", base_url="http://localhost:11434/v1", model_name="FL33TW00D-HF/dots.ocr")]
        responses = [
            _response(200, {"data": [{"id": "FL33TW00D-HF/dots.ocr"}]}, "http://localhost:11434/v1/models"),
            _response(503, {"error": "busy"}, "http://localhost:11434/v1/chat/completions"),
        ]
        client = _StubClient(responses)
        evidence = run_inference_smoke(targets=targets, client_factory=lambda **_: client)

        self.assertFalse(evidence["overall_success"])
        self.assertEqual(len(evidence["checks"]), 1)
        check = evidence["checks"][0]
        self.assertTrue(check["models_endpoint_ok"])
        self.assertFalse(check["completion_ok"])
        self.assertTrue(any("completion_check_failed" in err for err in check["errors"]))


if __name__ == "__main__":
    unittest.main()
