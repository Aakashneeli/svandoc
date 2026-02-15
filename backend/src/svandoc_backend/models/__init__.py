"""ORM model registry."""

from svandoc_backend.models.document import Document
from svandoc_backend.models.document_deletion_event import DocumentDeletionEvent
from svandoc_backend.models.export_artifact import ExportArtifact
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job
from svandoc_backend.models.user_correction import UserCorrection

__all__ = [
    "Document",
    "Job",
    "ExtractionResult",
    "UserCorrection",
    "ExportArtifact",
    "DocumentDeletionEvent",
]
