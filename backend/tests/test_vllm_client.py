import os
import unittest
from collections import deque
from typing import Any
from unittest.mock import patch

import httpx

from svandoc_backend.vllm_client import (
    VLLMClient,
    VLLMClientError,
    base_url_for_model,
    build_vllm_client_for_model,
)


class _StubHTTPClient:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = deque(responses)
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, headers: dict[str, str], json: dict[str, Any], timeout: float) -> httpx.Response:
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        item = self._responses.popleft()
        if isinstance(item, Exception):
            raise item
        return item


def _response(status_code: int, payload: dict[str, Any]) -> httpx.Response:
    request = httpx.Request("POST", "http://localhost:11434/v1/chat/completions")
    return httpx.Response(status_code=status_code, request=request, json=payload)


class VLLMClientTests(unittest.TestCase):
    def test_complete_success_single_attempt(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []
        stub = _StubHTTPClient(
            [
                _response(
                    200,
                    {"choices": [{"message": {"content": "{\"vendor\":\"Acme\"}"}}]},
                )
            ]
        )
        client = VLLMClient(
            base_url="http://localhost:11434/v1",
            api_key="test-key",
            metrics_hook=lambda event, payload: events.append((event, payload)),
            http_client=stub,
            sleep_fn=lambda _: None,
        )

        result = client.complete(model="dots.ocr", prompt="extract")

        self.assertEqual(result.text, "{\"vendor\":\"Acme\"}")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(stub.calls[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(events[0][0], "vllm.request")
        self.assertTrue(events[0][1]["success"])

    def test_complete_retries_on_503_then_succeeds(self) -> None:
        sleeps: list[float] = []
        stub = _StubHTTPClient(
            [
                _response(503, {"error": "busy"}),
                _response(200, {"choices": [{"message": {"content": "ok"}}]}),
            ]
        )
        client = VLLMClient(
            base_url="http://localhost:11434/v1",
            max_retries=2,
            retry_backoff_seconds=0.25,
            http_client=stub,
            sleep_fn=lambda seconds: sleeps.append(seconds),
        )

        result = client.complete(model="dots.ocr", prompt="extract")

        self.assertEqual(result.text, "ok")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(sleeps, [0.25])

    def test_complete_raises_after_retry_exhaustion(self) -> None:
        sleeps: list[float] = []
        timeout_error = httpx.TimeoutException("timeout")
        stub = _StubHTTPClient([timeout_error, timeout_error, timeout_error])
        client = VLLMClient(
            base_url="http://localhost:11434/v1",
            max_retries=2,
            retry_backoff_seconds=0.1,
            http_client=stub,
            sleep_fn=lambda seconds: sleeps.append(seconds),
        )

        with self.assertRaises(VLLMClientError):
            client.complete(model="dots.ocr", prompt="extract")

        self.assertEqual(sleeps, [0.1, 0.2])

    def test_complete_does_not_retry_on_400(self) -> None:
        sleeps: list[float] = []
        stub = _StubHTTPClient([_response(400, {"error": "bad request"})])
        client = VLLMClient(
            base_url="http://localhost:11434/v1",
            max_retries=3,
            http_client=stub,
            sleep_fn=lambda seconds: sleeps.append(seconds),
        )

        with self.assertRaises(VLLMClientError):
            client.complete(model="dots.ocr", prompt="extract")

        self.assertEqual(sleeps, [])
        self.assertEqual(len(stub.calls), 1)

    def test_base_url_for_model_uses_fallback_endpoint(self) -> None:
        env = {
            "VLLM_BASE_URL": "http://localhost:11434/v1",
            "VLLM_FALLBACK_BASE_URL": "http://localhost:11435/v1",
            "OCR_FALLBACK_MODEL": "datalab-to/chandra",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(base_url_for_model("rednote-hilab/dots.ocr"), "http://localhost:11434/v1")
            self.assertEqual(base_url_for_model("datalab-to/chandra"), "http://localhost:11435/v1")
            self.assertEqual(base_url_for_model("chandra"), "http://localhost:11435/v1")

    def test_build_vllm_client_for_model_selects_expected_base_url(self) -> None:
        env = {
            "VLLM_BASE_URL": "http://primary.example/v1",
            "VLLM_FALLBACK_BASE_URL": "http://fallback.example/v1",
            "OCR_FALLBACK_MODEL": "datalab-to/chandra",
        }
        with patch.dict(os.environ, env, clear=False):
            primary_client = build_vllm_client_for_model("rednote-hilab/dots.ocr")
            fallback_client = build_vllm_client_for_model("datalab-to/chandra")

        self.assertEqual(primary_client._base_url, "http://primary.example/v1")  # noqa: SLF001
        self.assertEqual(fallback_client._base_url, "http://fallback.example/v1")  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()

