"""Storage backend factory."""

from __future__ import annotations

import os

from svandoc_backend.storage.base import StorageBackend
from svandoc_backend.storage.local import LocalStorageBackend
from svandoc_backend.storage.s3_stub import S3StorageBackendStub


def storage_backend_name() -> str:
    raw = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    return raw or "local"


def get_storage_backend() -> StorageBackend:
    backend_name = storage_backend_name()
    if backend_name == "local":
        return LocalStorageBackend()
    if backend_name == "s3":
        return S3StorageBackendStub()
    raise ValueError(f"Unsupported STORAGE_BACKEND '{backend_name}'. Expected one of: local, s3.")
