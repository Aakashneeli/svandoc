"""S3-compatible stub backend for local development."""

from __future__ import annotations

import os
from pathlib import Path

from svandoc_backend.storage.base import StorageBackend
from svandoc_backend.uploads import safe_filename

DEFAULT_S3_BUCKET = "svandoc-dev"
DEFAULT_S3_STUB_PATH = "./data/s3-stub"


def s3_bucket_name() -> str:
    bucket = os.getenv("S3_BUCKET", DEFAULT_S3_BUCKET).strip()
    return bucket or DEFAULT_S3_BUCKET


def s3_stub_root() -> Path:
    configured_path = os.getenv("S3_STUB_STORAGE_PATH", DEFAULT_S3_STUB_PATH).strip()
    if not configured_path:
        configured_path = DEFAULT_S3_STUB_PATH
    return Path(configured_path)


class S3StorageBackendStub(StorageBackend):
    backend_name = "s3"

    def __init__(self, bucket: str | None = None, stub_root: Path | None = None) -> None:
        self._bucket = bucket or s3_bucket_name()
        self._stub_root = stub_root or s3_stub_root()

    def store_document(self, document_id: str, filename: str, content: bytes) -> str:
        safe_name = safe_filename(filename)

        # Persist locally so tests and local development can verify writes.
        local_target = self._stub_root / self._bucket / document_id / safe_name
        local_target.parent.mkdir(parents=True, exist_ok=True)
        local_target.write_bytes(content)

        return f"s3://{self._bucket}/{document_id}/{safe_name}"
