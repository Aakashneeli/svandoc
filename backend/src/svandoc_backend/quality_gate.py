"""Quality regression gate checks for benchmark evaluation output."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_QUALITY_EVAL_PATH = ".local-sandbox/quality-eval.json"
DEFAULT_THRESHOLD_METRIC = "f1"
DEFAULT_INVOICE_THRESHOLD = 0.92
DEFAULT_RECEIPT_THRESHOLD = 0.88


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value


def _quality_thresholds() -> dict[str, float]:
    return {
        "invoice": _read_float_env("QUALITY_THRESHOLD_INVOICE", DEFAULT_INVOICE_THRESHOLD),
        "receipt": _read_float_env("QUALITY_THRESHOLD_RECEIPT", DEFAULT_RECEIPT_THRESHOLD),
    }


def _quality_metric_name() -> str:
    raw = os.getenv("QUALITY_THRESHOLD_METRIC", DEFAULT_THRESHOLD_METRIC).strip().lower()
    if raw in {"precision", "recall", "f1"}:
        return raw
    return DEFAULT_THRESHOLD_METRIC


def _load_quality_eval(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_quality_gate(
    quality_eval: dict[str, Any],
    *,
    metric_name: str,
    thresholds: dict[str, float],
) -> tuple[bool, dict[str, Any]]:
    by_doc_type = quality_eval.get("by_doc_type", {})
    checks: dict[str, Any] = {}
    is_passing = True

    for doc_type, threshold in thresholds.items():
        overall = by_doc_type.get(doc_type, {}).get("overall", {})
        metric_value = overall.get(metric_name)
        if not isinstance(metric_value, (int, float)):
            checks[doc_type] = {
                "metric": metric_name,
                "actual": None,
                "threshold": threshold,
                "passed": False,
                "reason": "missing_metric",
            }
            is_passing = False
            continue

        actual = float(metric_value)
        passed = actual >= threshold
        checks[doc_type] = {
            "metric": metric_name,
            "actual": round(actual, 4),
            "threshold": threshold,
            "passed": passed,
            "reason": "ok" if passed else "below_threshold",
        }
        is_passing = is_passing and passed

    return is_passing, checks


def main() -> int:
    quality_eval_path = Path(os.getenv("QUALITY_EVAL_OUTPUT_PATH", DEFAULT_QUALITY_EVAL_PATH))
    metric_name = _quality_metric_name()
    thresholds = _quality_thresholds()

    if not quality_eval_path.exists():
        print(f"[quality-gate] quality evaluation file missing: {quality_eval_path}")
        return 1

    quality_eval = _load_quality_eval(quality_eval_path)
    is_passing, checks = evaluate_quality_gate(
        quality_eval,
        metric_name=metric_name,
        thresholds=thresholds,
    )
    for doc_type, result in checks.items():
        print(
            "[quality-gate] "
            f"doc_type={doc_type} metric={result['metric']} actual={result['actual']} "
            f"threshold={result['threshold']} passed={result['passed']} reason={result['reason']}"
        )

    if not is_passing:
        print("[quality-gate] failed: one or more quality checks are below threshold.")
        return 1

    print("[quality-gate] passed: all quality checks meet thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
