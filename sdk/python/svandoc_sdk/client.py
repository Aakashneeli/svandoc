from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class SvanDocClient:
    def __init__(self, *, api_base_url: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    def upload_document(self, *, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        content_type = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            with path.open("rb") as handle:
                response = client.post(
                    f"{self.api_base_url}/api/public/documents/upload",
                    headers=self._headers,
                    files={"files": (path.name, handle.read(), content_type)},
                )
            response.raise_for_status()
            return response.json()["data"]

    def get_job(self, job_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(
                f"{self.api_base_url}/api/public/jobs/{job_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()["data"]

    def get_extraction(self, document_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(
                f"{self.api_base_url}/api/public/documents/{document_id}/extraction",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()["data"]

    def export_document(self, document_id: str, *, export_format: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base_url}/api/public/documents/{document_id}/export",
                headers=self._headers,
                json={"format": export_format},
            )
            response.raise_for_status()
            return response.json()["data"]
