"""Local filesystem storage backend."""

from __future__ import annotations

import os
from pathlib import Path

from svandoc_backend.storage.base import StorageBackend
from svandoc_backend.uploads import safe_filename

DEFAULT_LOCAL_STORAGE_PATH = "./data/storage"


def local_storage_root() -> Path:
    configured_path = os.getenv("LOCAL_STORAGE_PATH", DEFAULT_LOCAL_STORAGE_PATH).strip()
    if not configured_path:
        configured_path = DEFAULT_LOCAL_STORAGE_PATH
    return Path(configured_path)


class LocalStorageBackend(StorageBackend):
    backend_name = "local"

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or local_storage_root()

    def store_document(self, document_id: str, filename: str, content: bytes) -> str:
        self._root.mkdir(parents=True, exist_ok=True)

        target = self._root / document_id / safe_filename(filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(target.resolve())
