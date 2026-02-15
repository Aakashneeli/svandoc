"""Chandra fallback OCR adapter using vLLM chat completions."""

from __future__ import annotations

import json
from base64 import b64encode
from typing import Any

from svandoc_backend.ocr_types import OCRExtractionResult
from svandoc_backend.vllm_client import VLLMClient

DEFAULT_CHANDRA_MODEL = "chandra"
REVIEW_CONFIDENCE_THRESHOLD = 0.85


class ChandraOCRAdapter:
    def __init__(self, client: VLLMClient, model_name: str = DEFAULT_CHANDRA_MODEL) -> None:
        self._client = client
        self._model_name = model_name

    def extract(
        self,
        *,
        document_content: bytes,
        mime_type: str,
        filename: str,
        doc_type_hint: str = "invoice",
    ) -> OCRExtractionResult:
        prompt = self._build_prompt(
            encoded_document=b64encode(document_content).decode("ascii"),
            mime_type=mime_type,
            filename=filename,
            doc_type_hint=doc_type_hint,
        )
        completion = self._client.complete(model=self._model_name, prompt=prompt)
        structured = _parse_model_json(completion.text)
        raw_text = str(structured.get("raw_text", ""))
        structured_payload = structured.get("structured_payload", {})
        confidence_map = structured.get("confidence_map", {})

        if not isinstance(structured_payload, dict):
            structured_payload = {}
        if not isinstance(confidence_map, dict):
            confidence_map = {}

        review_required = _is_review_required(confidence_map)
        return OCRExtractionResult(
            model=self._model_name,
            raw_text=raw_text,
            structured_payload=structured_payload,
            confidence_map=confidence_map,
            review_required=review_required,
        )

    def _build_prompt(
        self,
        *,
        encoded_document: str,
        mime_type: str,
        filename: str,
        doc_type_hint: str,
    ) -> str:
        return (
            "You are a fallback OCR extractor for difficult layouts.\n"
            "Return strict JSON with keys: raw_text, structured_payload, confidence_map.\n"
            "Focus on extracting line-items and tax breakdown with best effort.\n"
            f"doc_type_hint={doc_type_hint}\n"
            f"filename={filename}\n"
            f"mime_type={mime_type}\n"
            f"document_base64={encoded_document}\n"
        )


def _parse_model_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {"raw_text": "", "structured_payload": {}, "confidence_map": {}}

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {"raw_text": stripped, "structured_payload": {}, "confidence_map": {}}

    if isinstance(parsed, dict):
        return parsed
    return {"raw_text": stripped, "structured_payload": {}, "confidence_map": {}}


def _flatten_confidences(value: Any) -> list[float]:
    if isinstance(value, dict):
        values: list[float] = []
        for nested in value.values():
            values.extend(_flatten_confidences(nested))
        return values
    if isinstance(value, list):
        values = []
        for nested in value:
            values.extend(_flatten_confidences(nested))
        return values
    if isinstance(value, (int, float)):
        return [float(value)]
    return []


def _is_review_required(confidence_map: dict[str, Any]) -> bool:
    values = _flatten_confidences(confidence_map)
    if not values:
        return True
    return any(value < REVIEW_CONFIDENCE_THRESHOLD for value in values)
