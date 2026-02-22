"""Inference smoke validation for primary and fallback OCR endpoints."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_OUTPUT_PATH = ".local-sandbox/inference-smoke.json"
DEFAULT_PRIMARY_BASE_URL = "https://api.runpod.ai/v2/<primary-endpoint-id>/openai/v1"
DEFAULT_FALLBACK_BASE_URL = "https://api.runpod.ai/v2/<fallback-endpoint-id>/openai/v1"
DEFAULT_PRIMARY_MODEL = "rednote-hilab/dots.ocr"
DEFAULT_FALLBACK_MODEL = "datalab-to/chandra"
DEFAULT_RESULT_CODE_OK = "SMOKE_OK"

ENDPOINT_UNCONFIGURED = "ENDPOINT_UNCONFIGURED"
MODELS_UNREACHABLE = "MODELS_UNREACHABLE"
MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"
COMPLETION_FAILED = "COMPLETION_FAILED"


@dataclass(frozen=True)
class InferenceTarget:
    role: str
    base_url: str
    model_name: str
    endpoint_id: str | None = None


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _build_targets_from_env() -> list[InferenceTarget]:
    primary_url = os.getenv("VLLM_BASE_URL", DEFAULT_PRIMARY_BASE_URL).strip() or DEFAULT_PRIMARY_BASE_URL
    fallback_url = os.getenv("VLLM_FALLBACK_BASE_URL", DEFAULT_FALLBACK_BASE_URL).strip() or DEFAULT_FALLBACK_BASE_URL
    primary_model = os.getenv("OCR_DEFAULT_MODEL", DEFAULT_PRIMARY_MODEL).strip() or DEFAULT_PRIMARY_MODEL
    fallback_model = os.getenv("OCR_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL).strip() or DEFAULT_FALLBACK_MODEL
    primary_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID_PRIMARY", "").strip() or None
    fallback_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID_FALLBACK", "").strip() or None

    return [
        InferenceTarget(
            role="primary",
            base_url=primary_url,
            model_name=primary_model,
            endpoint_id=primary_endpoint_id,
        ),
        InferenceTarget(
            role="fallback",
            base_url=fallback_url,
            model_name=fallback_model,
            endpoint_id=fallback_endpoint_id,
        ),
    ]


def _models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _target_failure_code(target: InferenceTarget, suffix: str) -> str:
    prefix = (target.role or "target").strip().upper() or "TARGET"
    return f"{prefix}_{suffix}"


def _record_failure(target_check: dict[str, Any], code: str, message: str) -> None:
    failure_codes = target_check.setdefault("failure_codes", [])
    if code not in failure_codes:
        failure_codes.append(code)
    target_check.setdefault("errors", []).append(f"{code}:{message}")


def _is_endpoint_configured(base_url: str) -> bool:
    normalized = (base_url or "").strip()
    if not normalized:
        return False
    if "<" in normalized or ">" in normalized:
        return False
    if "replace-with-" in normalized or "replace-me" in normalized:
        return False
    return True


def run_inference_smoke(
    *,
    targets: list[InferenceTarget] | None = None,
    api_key: str | None = None,
    timeout_seconds: float | None = None,
    client_factory: Callable[..., httpx.Client] = httpx.Client,
) -> dict[str, Any]:
    effective_targets = targets or _build_targets_from_env()
    timeout = timeout_seconds or _read_float_env("INFERENCE_SMOKE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    checks: list[dict[str, Any]] = []
    all_ok = True

    with client_factory(timeout=timeout) as client:
        for target in effective_targets:
            target_check: dict[str, Any] = {
                "role": target.role,
                "base_url": target.base_url,
                "model": target.model_name,
                "endpoint_id": target.endpoint_id,
                "models_endpoint_ok": False,
                "completion_ok": False,
                "errors": [],
                "failure_codes": [],
                "status": "failed",
            }
            if not _is_endpoint_configured(target.base_url):
                all_ok = False
                _record_failure(
                    target_check,
                    _target_failure_code(target, ENDPOINT_UNCONFIGURED),
                    "Base URL is empty or contains placeholder markers.",
                )
                checks.append(target_check)
                continue

            try:
                models_response = client.get(_models_url(target.base_url), headers=headers, timeout=timeout)
                models_response.raise_for_status()
                payload = models_response.json()
                available_models = []
                if isinstance(payload, dict) and isinstance(payload.get("data"), list):
                    for item in payload["data"]:
                        if isinstance(item, dict) and item.get("id") is not None:
                            available_models.append(str(item["id"]))
                target_check["available_models"] = available_models
                target_check["models_endpoint_ok"] = True
                target_check["model_list_contains_target"] = target.model_name in available_models
                if not target_check["model_list_contains_target"]:
                    all_ok = False
                    _record_failure(
                        target_check,
                        _target_failure_code(target, MODEL_NOT_AVAILABLE),
                        f"Target model '{target.model_name}' was not listed by /models.",
                    )
            except Exception as exc:
                all_ok = False
                _record_failure(
                    target_check,
                    _target_failure_code(target, MODELS_UNREACHABLE),
                    f"{exc.__class__.__name__}:{exc}",
                )

            try:
                completion_response = client.post(
                    _chat_completions_url(target.base_url),
                    headers=headers,
                    json={
                        "model": target.model_name,
                        "messages": [
                            {
                                "role": "user",
                                "content": "Return compact JSON with key 'status' and value 'ok'.",
                            }
                        ],
                        "max_tokens": 32,
                        "temperature": 0.0,
                    },
                    timeout=timeout,
                )
                completion_response.raise_for_status()
                completion_payload = completion_response.json()
                target_check["completion_ok"] = True
                target_check["completion_preview"] = _extract_completion_preview(completion_payload)
            except Exception as exc:
                all_ok = False
                _record_failure(
                    target_check,
                    _target_failure_code(target, COMPLETION_FAILED),
                    f"{exc.__class__.__name__}:{exc}",
                )

            if not target_check["failure_codes"]:
                target_check["status"] = "ok"

            checks.append(target_check)

    failure_codes: list[str] = []
    for check in checks:
        for code in check.get("failure_codes", []):
            if isinstance(code, str) and code and code not in failure_codes:
                failure_codes.append(code)

    return {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "result_code": DEFAULT_RESULT_CODE_OK if all_ok else failure_codes[0],
        "overall_success": all_ok,
        "failure_codes": failure_codes,
        "checks": checks,
    }


def _extract_completion_preview(payload: dict[str, Any]) -> str:
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
    return str(content)[:200] if content is not None else ""


def _write_evidence(evidence: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def main() -> int:
    api_key = os.getenv("VLLM_API_KEY", "").strip() or None
    output_path = Path(os.getenv("INFERENCE_SMOKE_OUTPUT_PATH", DEFAULT_OUTPUT_PATH).strip() or DEFAULT_OUTPUT_PATH)

    evidence = run_inference_smoke(api_key=api_key)
    _write_evidence(evidence, output_path)
    print(f"[inference-smoke] evidence_path={output_path}")
    print(f"[inference-smoke] result_code={evidence['result_code']}")
    print(f"[inference-smoke] overall_success={evidence['overall_success']}")
    if not evidence["overall_success"]:
        print(f"[inference-smoke] failure_codes={','.join(evidence['failure_codes'])}")
    return 0 if bool(evidence.get("overall_success")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
