"""Upload helpers for file persistence and metadata extraction."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

DEFAULT_LOCAL_STORAGE_PATH = "./data/storage"


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def estimate_page_count(_content: bytes, _mime_type: str) -> int:
    return 1


def local_storage_root() -> Path:
    configured_path = os.getenv("LOCAL_STORAGE_PATH", DEFAULT_LOCAL_STORAGE_PATH).strip()
    if not configured_path:
        configured_path = DEFAULT_LOCAL_STORAGE_PATH
    return Path(configured_path)


def safe_filename(filename: str | None) -> str:
    cleaned = Path(filename or "upload.bin").name.strip()
    return cleaned or "upload.bin"


def persist_local_file(document_id: str, filename: str | None, content: bytes) -> str:
    root = local_storage_root()
    root.mkdir(parents=True, exist_ok=True)

    target = root / document_id / safe_filename(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return str(target.resolve())

