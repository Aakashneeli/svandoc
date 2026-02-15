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


@dataclass(frozen=True)
class InferenceTarget:
    role: str
    base_url: str
    model_name: str


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _build_targets_from_env() -> list[InferenceTarget]:
    primary_url = os.getenv("VLLM_BASE_URL", "http://localhost:11434/v1").strip() or "http://localhost:11434/v1"
    fallback_url = (
        os.getenv("VLLM_FALLBACK_BASE_URL", "http://localhost:11435/v1").strip() or "http://localhost:11435/v1"
    )
    primary_model = os.getenv("OCR_DEFAULT_MODEL", "FL33TW00D-HF/dots.ocr").strip() or "FL33TW00D-HF/dots.ocr"
    fallback_model = os.getenv("OCR_FALLBACK_MODEL", "datalab-to/chandra").strip() or "datalab-to/chandra"

    return [
        InferenceTarget(role="primary", base_url=primary_url, model_name=primary_model),
        InferenceTarget(role="fallback", base_url=fallback_url, model_name=fallback_model),
    ]


def _models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


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
                "models_endpoint_ok": False,
                "completion_ok": False,
                "errors": [],
            }
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
            except Exception as exc:
                all_ok = False
                target_check["errors"].append(f"models_check_failed:{exc.__class__.__name__}:{exc}")

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
                target_check["errors"].append(f"completion_check_failed:{exc.__class__.__name__}:{exc}")

            checks.append(target_check)

    return {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "overall_success": all_ok,
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
    print(f"[inference-smoke] overall_success={evidence['overall_success']}")
    return 0 if bool(evidence.get("overall_success")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
