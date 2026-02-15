"""Redis + Celery integration for asynchronous job processing."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from celery import Celery
from sqlalchemy.orm import Session, sessionmaker

from svandoc_backend.chandra_ocr import ChandraOCRAdapter
from svandoc_backend.db import SessionLocal
from svandoc_backend.dots_ocr import DotsOCRAdapter
from svandoc_backend.job_state_machine import can_transition, transition_job_status
from svandoc_backend.models.document import Document
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job
from svandoc_backend.preprocessing import preprocess_image_content
from svandoc_backend.vllm_client import build_vllm_client_from_env
from svandoc_backend.worker_logging import emit_worker_log

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_DOTS_MODEL = "dots.ocr"
DEFAULT_CHANDRA_MODEL = "chandra"

JOB_SESSION_FACTORY: sessionmaker[Session] = SessionLocal


def _read_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def queue_backend_mode() -> str:
    mode = os.getenv("QUEUE_BACKEND", "celery").strip().lower()
    return mode or "celery"


def _broker_url() -> str:
    value = os.getenv("REDIS_URL", DEFAULT_REDIS_URL).strip()
    return value or DEFAULT_REDIS_URL


def _dots_model_name() -> str:
    value = os.getenv("OCR_DEFAULT_MODEL", DEFAULT_DOTS_MODEL).strip()
    return value or DEFAULT_DOTS_MODEL


def _choose_ocr_adapter(model_name: str, client: object) -> DotsOCRAdapter | ChandraOCRAdapter:
    if model_name.lower() == DEFAULT_CHANDRA_MODEL:
        return ChandraOCRAdapter(client=client, model_name=model_name)
    return DotsOCRAdapter(client=client, model_name=model_name)


def _resolve_document_path(storage_uri: str) -> Path:
    if storage_uri.startswith("s3://"):
        path_without_scheme = storage_uri[len("s3://") :]
        parts = path_without_scheme.split("/", 1)
        if len(parts) != 2:
            raise FileNotFoundError(f"Invalid S3 URI: {storage_uri}")
        bucket, object_path = parts
        stub_root = os.getenv("S3_STUB_STORAGE_PATH", "./data/s3-stub").strip() or "./data/s3-stub"
        return Path(stub_root) / bucket / object_path
    return Path(storage_uri)


def _load_document_bytes(document: Document) -> bytes:
    path = _resolve_document_path(str(document.storage_uri))
    if not path.exists():
        raise FileNotFoundError(f"Document content not found: {path}")
    return path.read_bytes()


def _persist_extraction_result(
    session: Session,
    *,
    document_id: str,
    doc_type: str,
    model: str,
    raw_text: str,
    structured_payload: dict[str, object],
    confidence_map: dict[str, object],
    review_required: bool,
) -> None:
    existing = session.query(ExtractionResult).filter(ExtractionResult.document_id == document_id).one_or_none()
    if existing is None:
        existing = ExtractionResult(
            id=str(uuid4()),
            document_id=document_id,
            schema_version="v1",
            doc_type=doc_type,
            raw_ocr_text=raw_text,
            structured_payload=structured_payload,
            confidence_map=confidence_map,
            is_review_required=review_required,
        )
        session.add(existing)
    else:
        existing.raw_ocr_text = raw_text
        existing.structured_payload = structured_payload
        existing.confidence_map = confidence_map
        existing.is_review_required = review_required
        existing.doc_type = doc_type
    _ = model  # retained for future output persistence when fallback routing is added.


def create_celery_app() -> Celery:
    broker_url = _broker_url()
    app = Celery("svandoc")
    app.conf.update(
        broker_url=broker_url,
        result_backend=os.getenv("CELERY_RESULT_BACKEND", broker_url),
        task_always_eager=_read_bool_env("CELERY_TASK_ALWAYS_EAGER", False),
        task_eager_propagates=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )
    return app


celery_app = create_celery_app()


@celery_app.task(name="svandoc.jobs.process_document")
def process_document_job(job_id: str, request_id: str = "unknown") -> dict[str, str]:
    safe_request_id = request_id or "unknown"
    session = JOB_SESSION_FACTORY()
    try:
        job = session.get(Job, job_id)
        if job is None:
            emit_worker_log(
                event="job_missing",
                request_id=safe_request_id,
                job_id=job_id,
                document_id="unknown",
                status="missing",
            )
            return {"job_id": job_id, "status": "missing"}

        emit_worker_log(
            event="job_processing_started",
            request_id=safe_request_id,
            job_id=job.id,
            document_id=job.document_id,
            status="processing",
        )
        transition_job_status(job, "processing")
        session.commit()

        document = session.get(Document, job.document_id)
        if document is None:
            raise RuntimeError(f"Document not found for job {job_id}")

        raw_content = _load_document_bytes(document)
        preprocessed = preprocess_image_content(raw_content, str(document.mime_type))
        vllm_client = build_vllm_client_from_env()
        model_name = _dots_model_name()
        ocr_adapter = _choose_ocr_adapter(model_name, vllm_client)
        extraction = ocr_adapter.extract(
            document_content=preprocessed.content,
            mime_type=preprocessed.mime_type,
            filename=str(document.filename),
            doc_type_hint="invoice",
        )
        _persist_extraction_result(
            session,
            document_id=document.id,
            doc_type="invoice",
            model=extraction.model,
            raw_text=extraction.raw_text,
            structured_payload=extraction.structured_payload,
            confidence_map=extraction.confidence_map,
            review_required=extraction.review_required,
        )
        transition_job_status(job, "review_required" if extraction.review_required else "completed")
        session.commit()
        emit_worker_log(
            event="job_processing_completed",
            request_id=safe_request_id,
            job_id=job.id,
            document_id=job.document_id,
            status=str(job.status),
            details={
                "model": extraction.model,
                "preprocess_steps": list(preprocessed.applied_steps),
                "review_required": extraction.review_required,
            },
        )
        return {"job_id": job_id, "status": str(job.status)}
    except Exception as exc:  # pragma: no cover - defensive path
        session.rollback()
        failed_job = session.get(Job, job_id)
        if failed_job is not None and can_transition(str(failed_job.status), "failed"):
            transition_job_status(
                failed_job,
                "failed",
                error_code="PROCESSING_ERROR",
                error_message=str(exc),
            )
            session.commit()
            emit_worker_log(
                event="job_processing_failed",
                request_id=safe_request_id,
                job_id=failed_job.id,
                document_id=failed_job.document_id,
                status="failed",
                details={"error_code": "PROCESSING_ERROR", "error_message": str(exc)},
            )
        raise
    finally:
        session.close()


def enqueue_processing_job(job_id: str, request_id: str | None = None) -> str | None:
    if queue_backend_mode() == "disabled":
        return None

    async_result = process_document_job.delay(job_id, request_id or "unknown")
    return async_result.id
