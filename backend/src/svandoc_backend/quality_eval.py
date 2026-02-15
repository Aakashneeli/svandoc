"""Extraction quality evaluation against benchmark ground truth."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_GROUND_TRUTH_PATH = "datasets/benchmark/v1/ground_truth.json"
DEFAULT_PREDICTIONS_PATH = ".local-sandbox/quality-predictions.json"
DEFAULT_OUTPUT_PATH = ".local-sandbox/quality-eval.json"


@dataclass
class MetricCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _is_equal(left: Any, right: Any) -> bool:
    left_value = _normalize_scalar(left)
    right_value = _normalize_scalar(right)
    if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
        return abs(float(left_value) - float(right_value)) <= 1e-6
    return left_value == right_value


def _flatten_payload(value: Any, prefix: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            output.update(_flatten_payload(nested, next_prefix))
        return output
    if isinstance(value, list):
        for index, nested in enumerate(value):
            next_prefix = f"{prefix}.{index}" if prefix else str(index)
            output.update(_flatten_payload(nested, next_prefix))
        return output
    output[prefix] = value
    return output


def _extract_fields(record: dict[str, Any]) -> dict[str, Any]:
    direct = record.get("fields")
    if isinstance(direct, dict):
        return direct
    payload = record.get("structured_payload")
    if isinstance(payload, dict):
        return _flatten_payload(payload)
    return {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _to_sample_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        sample_id = str(record.get("sample_id", "")).strip()
        if not sample_id:
            continue
        indexed[sample_id] = record
    return indexed


def _build_metric_payload(counts: MetricCounts) -> dict[str, Any]:
    precision = counts.tp / (counts.tp + counts.fp) if (counts.tp + counts.fp) else 0.0
    recall = counts.tp / (counts.tp + counts.fn) if (counts.tp + counts.fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "tp": counts.tp,
        "fp": counts.fp,
        "fn": counts.fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_extraction_quality(
    *,
    ground_truth: dict[str, Any],
    predictions: dict[str, Any],
) -> dict[str, Any]:
    ground_samples = _to_sample_index(list(ground_truth.get("samples", [])))
    predicted_samples = _to_sample_index(list(predictions.get("samples", [])))

    field_counts_by_doc_type: dict[str, dict[str, MetricCounts]] = defaultdict(lambda: defaultdict(MetricCounts))
    aggregate_counts_by_doc_type: dict[str, MetricCounts] = defaultdict(MetricCounts)

    for sample_id, ground_sample in ground_samples.items():
        doc_type = str(ground_sample.get("doc_type", "unknown"))
        predicted_sample = predicted_samples.get(sample_id, {})

        ground_fields = _extract_fields(ground_sample)
        predicted_fields = _extract_fields(predicted_sample)
        all_paths = set(ground_fields.keys()) | set(predicted_fields.keys())

        for path in sorted(all_paths):
            counts = field_counts_by_doc_type[doc_type][path]
            aggregate = aggregate_counts_by_doc_type[doc_type]
            has_ground = path in ground_fields
            has_predicted = path in predicted_fields

            if has_ground and has_predicted:
                if _is_equal(ground_fields[path], predicted_fields[path]):
                    counts.tp += 1
                    aggregate.tp += 1
                else:
                    counts.fp += 1
                    counts.fn += 1
                    aggregate.fp += 1
                    aggregate.fn += 1
            elif has_ground and not has_predicted:
                counts.fn += 1
                aggregate.fn += 1
            elif has_predicted and not has_ground:
                counts.fp += 1
                aggregate.fp += 1

    doc_type_metrics: dict[str, Any] = {}
    for doc_type, field_counts in field_counts_by_doc_type.items():
        doc_type_metrics[doc_type] = {
            "overall": _build_metric_payload(aggregate_counts_by_doc_type[doc_type]),
            "fields": {
                field_path: _build_metric_payload(counts)
                for field_path, counts in sorted(field_counts.items())
            },
        }

    return {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "dataset_version": ground_truth.get("version"),
        "predictions_version": predictions.get("version"),
        "sample_count": len(ground_samples),
        "evaluated_prediction_count": len(predicted_samples),
        "by_doc_type": doc_type_metrics,
    }


def _write_output(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main() -> int:
    ground_truth_path = Path(os.getenv("QUALITY_EVAL_GROUND_TRUTH_PATH", DEFAULT_GROUND_TRUTH_PATH))
    predictions_path = Path(os.getenv("QUALITY_EVAL_PREDICTIONS_PATH", DEFAULT_PREDICTIONS_PATH))
    output_path = Path(os.getenv("QUALITY_EVAL_OUTPUT_PATH", DEFAULT_OUTPUT_PATH))

    if not ground_truth_path.exists():
        print(f"[quality-eval] ground truth file missing: {ground_truth_path}")
        return 1
    if not predictions_path.exists():
        print(f"[quality-eval] predictions file missing: {predictions_path}")
        return 1

    ground_truth = _load_json(ground_truth_path)
    predictions = _load_json(predictions_path)
    result = evaluate_extraction_quality(ground_truth=ground_truth, predictions=predictions)
    _write_output(result, output_path)
    print(f"[quality-eval] output_path={output_path}")
    for doc_type, metrics in result["by_doc_type"].items():
        overall = metrics["overall"]
        print(
            "[quality-eval] "
            f"doc_type={doc_type} precision={overall['precision']} recall={overall['recall']} f1={overall['f1']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
