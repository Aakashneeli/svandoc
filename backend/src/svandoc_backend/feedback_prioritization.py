"""Feedback prioritization helpers for v1.1 hardening backlog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_feedback_items(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def prioritize_feedback(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for item in items:
        impact = _safe_int(item.get("impact"), default=1)
        effort = _safe_int(item.get("effort"), default=1)
        frequency = _safe_int(item.get("frequency"), default=1)
        score = round((impact * frequency) / effort, 4)
        ranked.append(
            {
                "id": str(item.get("id", "")).strip() or "unknown",
                "title": str(item.get("title", "")).strip() or "Untitled",
                "impact": impact,
                "effort": effort,
                "frequency": frequency,
                "owner": str(item.get("owner", "unassigned")).strip() or "unassigned",
                "notes": str(item.get("notes", "")).strip(),
                "priority_score": score,
            }
        )

    ranked.sort(
        key=lambda item: (
            -float(item["priority_score"]),
            -int(item["impact"]),
            int(item["effort"]),
            str(item["id"]),
        )
    )
    return ranked


def run_feedback_prioritization(input_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    items = load_feedback_items(input_path)
    ranked = prioritize_feedback(items)
    Path(output_path).write_text(
        json.dumps({"ranked_items": ranked}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ranked


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prioritize pilot feedback for v1.1 hardening backlog.")
    parser.add_argument("--input", required=True, help="Path to feedback items JSON.")
    parser.add_argument("--out", required=True, help="Path to ranked backlog JSON output.")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    ranked = run_feedback_prioritization(args.input, args.out)
    print(json.dumps({"top_5": ranked[:5], "count": len(ranked)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

