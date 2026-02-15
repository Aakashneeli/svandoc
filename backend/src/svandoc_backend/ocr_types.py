"""Shared OCR extraction result types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OCRExtractionResult:
    model: str
    raw_text: str
    structured_payload: dict[str, Any]
    confidence_map: dict[str, Any]
    review_required: bool
