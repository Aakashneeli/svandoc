"""Storage backend abstractions for document persistence."""

from svandoc_backend.storage.base import StorageBackend
from svandoc_backend.storage.factory import get_storage_backend
from svandoc_backend.storage.local import LocalStorageBackend
from svandoc_backend.storage.s3_stub import S3StorageBackendStub

__all__ = [
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackendStub",
    "get_storage_backend",
]
