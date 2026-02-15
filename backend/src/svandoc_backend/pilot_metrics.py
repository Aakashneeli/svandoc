"""Pilot workflow metrics computation helpers."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any


@dataclass(frozen=True)
class PilotSession:
    session_id: str
    user_segment: str
    documents_uploaded: int
    completed_workflow: bool
    time_to_first_export_seconds: int | None
    corrections_count: int


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _parse_int(value: str, default: int = 0) -> int:
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def load_pilot_sessions(csv_path: str | Path) -> list[PilotSession]:
    path = Path(csv_path)
    sessions: list[PilotSession] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sessions.append(
                PilotSession(
                    session_id=str(row.get("session_id", "")).strip(),
                    user_segment=str(row.get("user_segment", "")).strip(),
                    documents_uploaded=_parse_int(str(row.get("documents_uploaded", "")), default=0),
                    completed_workflow=_parse_bool(str(row.get("completed_workflow", ""))),
                    time_to_first_export_seconds=(
                        _parse_int(str(row.get("time_to_first_export_seconds", "")), default=0)
                        if str(row.get("time_to_first_export_seconds", "")).strip()
                        else None
                    ),
                    corrections_count=_parse_int(str(row.get("corrections_count", "")), default=0),
                )
            )
    return sessions


def evaluate_pilot_metrics(sessions: list[PilotSession]) -> dict[str, Any]:
    total_sessions = len(sessions)
    completed_sessions = [item for item in sessions if item.completed_workflow]
    completed_count = len(completed_sessions)
    completion_rate = (completed_count / total_sessions) if total_sessions else 0.0

    completed_times = [
        item.time_to_first_export_seconds
        for item in completed_sessions
        if item.time_to_first_export_seconds is not None and item.time_to_first_export_seconds > 0
    ]
    median_time_seconds = int(median(completed_times)) if completed_times else None
    average_time_seconds = (
        round(sum(completed_times) / len(completed_times), 2)
        if completed_times
        else None
    )
    average_corrections = (
        round(sum(item.corrections_count for item in completed_sessions) / completed_count, 2)
        if completed_count
        else None
    )

    return {
        "summary": {
            "total_sessions": total_sessions,
            "completed_sessions": completed_count,
            "completion_rate": round(completion_rate, 4),
            "completion_rate_percent": round(completion_rate * 100, 2),
            "median_time_to_value_seconds": median_time_seconds,
            "average_time_to_value_seconds": average_time_seconds,
            "average_corrections_completed_sessions": average_corrections,
        },
        "sessions": [
            {
                "session_id": item.session_id,
                "user_segment": item.user_segment,
                "documents_uploaded": item.documents_uploaded,
                "completed_workflow": item.completed_workflow,
                "time_to_first_export_seconds": item.time_to_first_export_seconds,
                "corrections_count": item.corrections_count,
            }
            for item in sessions
        ],
    }


def run_pilot_metrics(csv_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    sessions = load_pilot_sessions(csv_path)
    result = evaluate_pilot_metrics(sessions)
    Path(output_path).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate pilot workflow metrics from session CSV.")
    parser.add_argument("--csv", required=True, help="Path to pilot sessions CSV file.")
    parser.add_argument("--out", required=True, help="Path to JSON output file.")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = run_pilot_metrics(args.csv, args.out)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

