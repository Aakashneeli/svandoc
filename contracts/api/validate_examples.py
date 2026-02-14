"""Validates API envelope examples without third-party dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


EXAMPLES = [
    Path("examples/success-upload.json"),
    Path("examples/error-validation.json"),
]

ISO_8601_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_object(value: Any) -> bool:
    return isinstance(value, dict)


def validate_error_object(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["code", "message", "retryable"]
    for field in required:
        if field not in payload:
            errors.append(f"missing error.{field}")
    if "code" in payload and (not isinstance(payload["code"], str) or not payload["code"]):
        errors.append("error.code must be a non-empty string")
    if "message" in payload and (not isinstance(payload["message"], str) or not payload["message"]):
        errors.append("error.message must be a non-empty string")
    if "retryable" in payload and not isinstance(payload["retryable"], bool):
        errors.append("error.retryable must be boolean")
    if "details" in payload and not isinstance(payload["details"], (dict, list, type(None))):
        errors.append("error.details must be object, array, or null")
    return errors


def validate_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    required = ["status", "request_id", "timestamp", "data", "error", "meta"]
    for field in required:
        if field not in envelope:
            errors.append(f"missing {field}")

    if errors:
        return errors

    if envelope["status"] not in {"success", "error"}:
        errors.append("status must be success or error")

    if not isinstance(envelope["request_id"], str) or not envelope["request_id"]:
        errors.append("request_id must be a non-empty string")

    if not isinstance(envelope["timestamp"], str) or not ISO_8601_UTC_PATTERN.match(
        envelope["timestamp"]
    ):
        errors.append("timestamp must be UTC ISO-8601 format (YYYY-MM-DDTHH:MM:SSZ)")

    if not is_object(envelope["meta"]):
        errors.append("meta must be an object")

    status = envelope["status"]
    if status == "success":
        if envelope["error"] is not None:
            errors.append("error must be null for success responses")
        if envelope["data"] is None:
            errors.append("data must be non-null for success responses")
    elif status == "error":
        if envelope["data"] is not None:
            errors.append("data must be null for error responses")
        if not is_object(envelope["error"]):
            errors.append("error must be an object for error responses")
        else:
            errors.extend(validate_error_object(envelope["error"]))

    return errors


def main() -> int:
    root = Path(__file__).parent
    failures = 0
    for rel_path in EXAMPLES:
        example_path = root / rel_path
        payload = load_json(example_path)
        issues = validate_envelope(payload)
        if issues:
            failures += 1
            print(f"[FAIL] {example_path}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"[PASS] {example_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
