"""Deploy gate checks for RunPod inference readiness."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from svandoc_backend.inference_smoke import DEFAULT_RESULT_CODE_OK, run_inference_smoke

DEFAULT_OUTPUT_PATH = ".local-sandbox/runpod-readiness-gate.json"
REQUIRED_ROLES = ("primary", "fallback")


def evaluate_runpod_readiness(smoke_evidence: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    checks_raw = smoke_evidence.get("checks")
    checks = checks_raw if isinstance(checks_raw, list) else []
    checks_by_role: dict[str, dict[str, Any]] = {}
    for item in checks:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        if role:
            checks_by_role[role] = item

    blocking_failures: list[str] = []
    role_status: dict[str, str] = {}

    for role in REQUIRED_ROLES:
        check = checks_by_role.get(role)
        if check is None:
            blocking_failures.append(f"{role.upper()}_CHECK_MISSING")
            role_status[role] = "missing"
            continue

        status = str(check.get("status", "failed"))
        role_status[role] = status
        if status != "ok":
            failure_codes = check.get("failure_codes")
            if isinstance(failure_codes, list) and failure_codes:
                for code in failure_codes:
                    if isinstance(code, str):
                        blocking_failures.append(code)
            else:
                blocking_failures.append(f"{role.upper()}_CHECK_FAILED")

    if str(smoke_evidence.get("result_code", "")) != DEFAULT_RESULT_CODE_OK:
        blocking_failures.append(str(smoke_evidence.get("result_code", "UNKNOWN_RESULT_CODE")))
    if not bool(smoke_evidence.get("overall_success")):
        blocking_failures.append("OVERALL_SUCCESS_FALSE")

    deduped_failures = list(dict.fromkeys(code for code in blocking_failures if code))
    passed = len(deduped_failures) == 0
    summary = {
        "passed": passed,
        "result_code": smoke_evidence.get("result_code"),
        "overall_success": bool(smoke_evidence.get("overall_success")),
        "required_roles": list(REQUIRED_ROLES),
        "role_status": role_status,
        "blocking_failures": deduped_failures,
    }
    return passed, summary


def _write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    api_key = os.getenv("VLLM_API_KEY", "").strip() or None
    output_path = Path(os.getenv("RUNPOD_READINESS_OUTPUT_PATH", DEFAULT_OUTPUT_PATH).strip() or DEFAULT_OUTPUT_PATH)

    smoke_evidence = run_inference_smoke(api_key=api_key)
    passed, summary = evaluate_runpod_readiness(smoke_evidence)
    evidence = {
        "summary": summary,
        "smoke_evidence": smoke_evidence,
    }
    _write_evidence(output_path, evidence)

    print(f"[runpod-readiness-gate] evidence_path={output_path}")
    print(f"[runpod-readiness-gate] passed={summary['passed']}")
    print(f"[runpod-readiness-gate] result_code={summary['result_code']}")
    if not passed:
        print(f"[runpod-readiness-gate] blocking_failures={','.join(summary['blocking_failures'])}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
