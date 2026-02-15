"""vLLM HTTP client with retry policy and metrics hook support."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

DEFAULT_VLLM_BASE_URL = "http://localhost:11434/v1"
DEFAULT_VLLM_FALLBACK_BASE_URL = "http://localhost:11435/v1"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5
DEFAULT_FALLBACK_MODEL = "datalab-to/chandra"


class VLLMClientError(RuntimeError):
    """Raised for vLLM request failures."""


@dataclass(frozen=True)
class VLLMCompletionResult:
    model: str
    text: str
    response_payload: dict[str, Any]
    attempts: int
    latency_ms: int


MetricsHook = Callable[[str, dict[str, Any]], None]


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _read_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def _is_retryable_http_error(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _model_basename(model_name: str) -> str:
    clean = (model_name or "").strip().lower()
    if "/" in clean:
        return clean.rsplit("/", 1)[-1]
    return clean


def is_fallback_model(model_name: str, fallback_model_name: str) -> bool:
    model = (model_name or "").strip().lower()
    fallback = (fallback_model_name or "").strip().lower()
    if not model or not fallback:
        return False
    return model == fallback or _model_basename(model) == _model_basename(fallback)


def base_url_for_model(model_name: str) -> str:
    primary_url = os.getenv("VLLM_BASE_URL", DEFAULT_VLLM_BASE_URL).strip() or DEFAULT_VLLM_BASE_URL
    fallback_url = (
        os.getenv("VLLM_FALLBACK_BASE_URL", DEFAULT_VLLM_FALLBACK_BASE_URL).strip()
        or DEFAULT_VLLM_FALLBACK_BASE_URL
    )
    fallback_model_name = os.getenv("OCR_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL).strip() or DEFAULT_FALLBACK_MODEL
    return fallback_url if is_fallback_model(model_name, fallback_model_name) else primary_url


class VLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
        metrics_hook: MetricsHook | None = None,
        http_client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._metrics_hook = metrics_hook
        self._http_client = http_client or httpx.Client(timeout=self._timeout_seconds)
        self._sleep_fn = sleep_fn or time.sleep

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        extra_payload: dict[str, Any] | None = None,
    ) -> VLLMCompletionResult:
        request_payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if extra_payload:
            request_payload.update(extra_payload)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        attempt = 0
        start = time.perf_counter()
        last_error: Exception | None = None

        while attempt <= self._max_retries:
            attempt += 1
            try:
                response = self._http_client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=request_payload,
                    timeout=self._timeout_seconds,
                )
                if _is_retryable_http_error(response.status_code):
                    raise httpx.HTTPStatusError(
                        f"Retryable vLLM status: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                payload = response.json()
                text = _extract_text(payload)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                self._emit_metric(
                    "vllm.request",
                    {
                        "success": True,
                        "attempts": attempt,
                        "latency_ms": elapsed_ms,
                        "model": model,
                    },
                )
                return VLLMCompletionResult(
                    model=model,
                    text=text,
                    response_payload=payload,
                    attempts=attempt,
                    latency_ms=elapsed_ms,
                )
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                should_retry = _should_retry_exception(exc)
                if not should_retry or attempt > self._max_retries:
                    break
                sleep_seconds = self._retry_backoff_seconds * (2 ** (attempt - 1))
                self._sleep_fn(sleep_seconds)
            except Exception as exc:
                last_error = exc
                break

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        self._emit_metric(
            "vllm.request",
            {
                "success": False,
                "attempts": attempt,
                "latency_ms": elapsed_ms,
                "model": model,
                "error_type": last_error.__class__.__name__ if last_error else "UnknownError",
            },
        )
        raise VLLMClientError(f"vLLM request failed after {attempt} attempt(s)") from last_error

    def _emit_metric(self, event: str, payload: dict[str, Any]) -> None:
        if self._metrics_hook is None:
            return
        self._metrics_hook(event, payload)


def _extract_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return str(content) if content is not None else ""


def _should_retry_exception(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return _is_retryable_http_error(exc.response.status_code)
    return False


def build_vllm_client_from_env(
    *,
    metrics_hook: MetricsHook | None = None,
    http_client: httpx.Client | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> VLLMClient:
    base_url = os.getenv("VLLM_BASE_URL", DEFAULT_VLLM_BASE_URL).strip() or DEFAULT_VLLM_BASE_URL
    api_key = os.getenv("VLLM_API_KEY", "").strip() or None
    timeout_seconds = _read_float_env("VLLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    max_retries = _read_int_env("VLLM_MAX_RETRIES", DEFAULT_MAX_RETRIES)
    retry_backoff_seconds = _read_float_env("VLLM_RETRY_BACKOFF_SECONDS", DEFAULT_RETRY_BACKOFF_SECONDS)

    return VLLMClient(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        metrics_hook=metrics_hook,
        http_client=http_client,
        sleep_fn=sleep_fn,
    )


def build_vllm_client_for_model(
    model_name: str,
    *,
    metrics_hook: MetricsHook | None = None,
    http_client: httpx.Client | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> VLLMClient:
    api_key = os.getenv("VLLM_API_KEY", "").strip() or None
    timeout_seconds = _read_float_env("VLLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    max_retries = _read_int_env("VLLM_MAX_RETRIES", DEFAULT_MAX_RETRIES)
    retry_backoff_seconds = _read_float_env("VLLM_RETRY_BACKOFF_SECONDS", DEFAULT_RETRY_BACKOFF_SECONDS)

    return VLLMClient(
        base_url=base_url_for_model(model_name),
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        metrics_hook=metrics_hook,
        http_client=http_client,
        sleep_fn=sleep_fn,
    )
