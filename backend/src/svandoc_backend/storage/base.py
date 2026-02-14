"""Core storage backend interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Interface implemented by all storage backends."""

    backend_name: str

    @abstractmethod
    def store_document(self, document_id: str, filename: str, content: bytes) -> str:
        """Persist a document and return its storage URI."""
