"""FastAPI application bootstrap for svanDoc backend."""

from __future__ import annotations

import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from sqlalchemy.orm import Session

from svandoc_backend import __version__
from svandoc_backend.db import get_db_session
from svandoc_backend.envelope import error_envelope, request_id_from_request, success_envelope
from svandoc_backend.export_service import build_csv_export, build_json_export, build_xlsx_export
from svandoc_backend.models.document import Document
from svandoc_backend.models.export_artifact import ExportArtifact
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job
from svandoc_backend.models.user_correction import UserCorrection
from svandoc_backend.queueing import enqueue_processing_job
from svandoc_backend.storage import get_storage_backend
from svandoc_backend.uploads import (
    compute_checksum,
    normalized_mime_type,
    safe_filename,
    validate_upload,
)

app = FastAPI(
    title="svanDoc Backend API",
    version=__version__,
)


class CorrectionInput(BaseModel):
    field_path: str = Field(..., min_length=1)
    new_value: Any


class ExtractionCorrectionRequest(BaseModel):
    corrections: list[CorrectionInput] = Field(..., min_length=1)


class ExportRequest(BaseModel):
    format: str = Field(..., min_length=1)


def _iso_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_field_token(token: str) -> str | int:
    if token.isdigit():
        return int(token)
    return token


def _get_path_value(payload: Any, field_path: str) -> tuple[bool, Any]:
    current = payload
    for token in field_path.split("."):
        parsed = _parse_field_token(token)
        if isinstance(parsed, int):
            if not isinstance(current, list) or parsed < 0 or parsed >= len(current):
                return False, None
            current = current[parsed]
            continue
        if not isinstance(current, dict) or parsed not in current:
            return False, None
        current = current[parsed]
    return True, current


def _set_path_value(payload: Any, field_path: str, value: Any) -> bool:
    current = payload
    tokens = field_path.split(".")
    for index, token in enumerate(tokens):
        is_last = index == len(tokens) - 1
        parsed = _parse_field_token(token)
        if isinstance(parsed, int):
            if not isinstance(current, list) or parsed < 0 or parsed >= len(current):
                return False
            if is_last:
                current[parsed] = value
                return True
            current = current[parsed]
            continue
        if not isinstance(current, dict) or parsed not in current:
            return False
        if is_last:
            current[parsed] = value
            return True
        current = current[parsed]
    return False


def _normalize_export_format(raw_format: str) -> str:
    return (raw_format or "").strip().lower()


def queue_backend_mode() -> str:
    mode = os.getenv("QUEUE_BACKEND", "celery").strip().lower()
    return mode or "celery"


def redis_url() -> str:
    value = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    return value or "redis://localhost:6379/0"


def check_database_ready(db: Session) -> tuple[bool, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive check path
        return False, f"error:{exc.__class__.__name__}"
    return True, "ok"


def check_redis_ready() -> tuple[bool, str]:
    if queue_backend_mode() == "disabled":
        return True, "skipped"

    try:
        client = Redis.from_url(redis_url(), socket_connect_timeout=2, socket_timeout=2)
        client.ping()
    except RedisError as exc:
        return False, f"error:{exc.__class__.__name__}"
    return True, "ok"


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    return success_envelope(
        request,
        data={
            "service": "svandoc-backend",
            "status": "ok",
        },
    )


@app.get("/ready")
async def ready(request: Request, db: Session = Depends(get_db_session)) -> dict[str, object]:
    db_ok, db_status = check_database_ready(db)
    redis_ok, redis_status = check_redis_ready()
    is_ready = db_ok and redis_ok

    checks = {
        "api": "ok",
        "database": db_status,
        "redis": redis_status,
    }

    if not is_ready:
        return JSONResponse(
            status_code=503,
            content=error_envelope(
                request,
                code="DEPENDENCY_UNAVAILABLE",
                message="One or more dependencies are unavailable.",
                details={"checks": checks},
                retryable=True,
            ),
        )

    return success_envelope(
        request,
        data={
            "service": "svandoc-backend",
            "status": "ready",
            "checks": checks,
        },
    )


@app.get("/api/jobs/{job_id}")
async def get_job_status(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    job = db.get(Job, job_id)
    if job is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="JOB_NOT_FOUND",
                message="Requested job does not exist.",
                details={"job_id": job_id},
                retryable=False,
            ),
        )

    return success_envelope(
        request,
        data={
            "job_id": str(job.id),
            "document_id": str(job.document_id),
            "status": str(job.status),
            "attempt_count": int(job.attempt_count),
            "started_at": _iso_timestamp(job.started_at),
            "finished_at": _iso_timestamp(job.finished_at),
            "created_at": _iso_timestamp(job.created_at),
            "error": (
                {
                    "code": str(job.error_code),
                    "message": str(job.error_message),
                }
                if job.error_code or job.error_message
                else None
            ),
        },
    )


@app.get("/api/documents/{document_id}/extraction")
async def get_document_extraction(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="DOCUMENT_NOT_FOUND",
                message="Requested document does not exist.",
                details={"document_id": document_id},
                retryable=False,
            ),
        )

    extraction = (
        db.query(ExtractionResult).filter(ExtractionResult.document_id == document_id).one_or_none()
    )
    if extraction is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="EXTRACTION_NOT_FOUND",
                message="Extraction result is not available for this document.",
                details={"document_id": document_id},
                retryable=False,
            ),
        )

    return success_envelope(
        request,
        data={
            "document_id": str(document.id),
            "schema_version": str(extraction.schema_version),
            "doc_type": str(extraction.doc_type),
            "review_required": bool(extraction.is_review_required),
            "raw_ocr_text": str(extraction.raw_ocr_text),
            "structured_payload": extraction.structured_payload,
            "confidence_map": extraction.confidence_map,
            "created_at": _iso_timestamp(extraction.created_at),
            "updated_at": _iso_timestamp(extraction.updated_at),
        },
    )


@app.patch("/api/documents/{document_id}/extraction")
async def patch_document_extraction(
    request: Request,
    document_id: str,
    correction_request: ExtractionCorrectionRequest,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="DOCUMENT_NOT_FOUND",
                message="Requested document does not exist.",
                details={"document_id": document_id},
                retryable=False,
            ),
        )

    extraction = (
        db.query(ExtractionResult).filter(ExtractionResult.document_id == document_id).one_or_none()
    )
    if extraction is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="EXTRACTION_NOT_FOUND",
                message="Extraction result is not available for this document.",
                details={"document_id": document_id},
                retryable=False,
            ),
        )

    updated_payload = deepcopy(extraction.structured_payload)
    corrections: list[dict[str, Any]] = []
    invalid_paths: list[str] = []

    for correction in correction_request.corrections:
        exists, old_value = _get_path_value(updated_payload, correction.field_path)
        if not exists:
            invalid_paths.append(correction.field_path)
            continue
        if not _set_path_value(updated_payload, correction.field_path, correction.new_value):
            invalid_paths.append(correction.field_path)
            continue
        corrections.append(
            {
                "field_path": correction.field_path,
                "old_value": old_value,
                "new_value": correction.new_value,
            }
        )

    if invalid_paths:
        return JSONResponse(
            status_code=400,
            content=error_envelope(
                request,
                code="VALIDATION_ERROR",
                message="One or more correction paths are invalid.",
                details={"invalid_field_paths": invalid_paths},
                retryable=False,
            ),
        )

    corrected_by = request.headers.get("x-user-id", "local-user")
    correction_time = datetime.now(timezone.utc)
    for correction in corrections:
        db.add(
            UserCorrection(
                id=str(uuid4()),
                document_id=document_id,
                field_path=str(correction["field_path"]),
                old_value=correction["old_value"],
                new_value=correction["new_value"],
                corrected_by=corrected_by,
                corrected_at=correction_time,
            )
        )

    extraction.structured_payload = updated_payload
    extraction.updated_at = correction_time
    db.commit()

    return success_envelope(
        request,
        data={
            "document_id": document_id,
            "correction_count": len(corrections),
            "corrected_by": corrected_by,
            "corrected_at": _iso_timestamp(correction_time),
            "structured_payload": extraction.structured_payload,
            "confidence_map": extraction.confidence_map,
            "review_required": bool(extraction.is_review_required),
        },
    )


@app.post("/api/documents/{document_id}/export")
async def export_document(
    request: Request,
    document_id: str,
    export_request: ExportRequest,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    export_format = _normalize_export_format(export_request.format)
    if export_format not in {"json", "csv", "xlsx"}:
        return JSONResponse(
            status_code=400,
            content=error_envelope(
                request,
                code="VALIDATION_ERROR",
                message="Unsupported export format.",
                details={"format": export_request.format, "supported_formats": ["json", "csv", "xlsx"]},
                retryable=False,
            ),
        )

    document = db.get(Document, document_id)
    if document is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="DOCUMENT_NOT_FOUND",
                message="Requested document does not exist.",
                details={"document_id": document_id},
                retryable=False,
            ),
        )

    extraction = (
        db.query(ExtractionResult).filter(ExtractionResult.document_id == document_id).one_or_none()
    )
    if extraction is None:
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                request,
                code="EXTRACTION_NOT_FOUND",
                message="Extraction result is not available for this document.",
                details={"document_id": document_id},
                retryable=False,
            ),
        )

    try:
        storage_backend = get_storage_backend()
    except ValueError as exc:
        return JSONResponse(
            status_code=500,
            content=error_envelope(
                request,
                code="CONFIGURATION_ERROR",
                message=str(exc),
                details=None,
                retryable=False,
            ),
        )

    payload = extraction.structured_payload
    if export_format == "json":
        export_content = build_json_export(payload)
    elif export_format == "csv":
        export_content = build_csv_export(payload)
    else:
        export_content = build_xlsx_export(payload)

    artifact_id = str(uuid4())
    artifact_filename = f"{document_id}.{export_format}"
    storage_uri = storage_backend.store_document(artifact_id, artifact_filename, export_content)
    created_by = request.headers.get("x-user-id", "local-user")
    created_at = datetime.now(timezone.utc)

    artifact = ExportArtifact(
        id=artifact_id,
        document_id=document_id,
        format=export_format,
        storage_uri=storage_uri,
        created_by=created_by,
        created_at=created_at,
    )
    db.add(artifact)
    db.commit()

    return success_envelope(
        request,
        data={
            "artifact_id": artifact_id,
            "document_id": document_id,
            "format": export_format,
            "storage_uri": storage_uri,
            "created_by": created_by,
            "created_at": _iso_timestamp(created_at),
        },
    )


@app.post("/api/documents/upload")
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    doc_type_hint: str | None = Form(None),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    del doc_type_hint
    worker_request_id = request_id_from_request(request)

    try:
        storage_backend = get_storage_backend()
    except ValueError as exc:
        return JSONResponse(
            status_code=500,
            content=error_envelope(
                request,
                code="CONFIGURATION_ERROR",
                message=str(exc),
                details=None,
                retryable=False,
            ),
        )

    document_ids: list[str] = []
    job_ids: list[str] = []
    team_id = request.headers.get("x-team-id", "local-team")
    uploaded_by = request.headers.get("x-user-id", "local-user")
    prepared_uploads: list[dict[str, object]] = []
    validation_details: list[dict[str, object]] = []

    for upload in files:
        content = await upload.read()
        mime_type = normalized_mime_type(upload.content_type)
        filename = safe_filename(upload.filename)
        issues, page_count = validate_upload(filename, mime_type, content)
        if issues:
            validation_details.append(
                {
                    "filename": filename,
                    "issues": issues,
                }
            )
            continue

        prepared_uploads.append(
            {
                "filename": filename,
                "mime_type": mime_type,
                "content": content,
                "checksum": compute_checksum(content),
                "page_count": page_count,
            }
        )

    if validation_details:
        return JSONResponse(
            status_code=400,
            content=error_envelope(
                request,
                code="VALIDATION_ERROR",
                message="One or more files are invalid.",
                details={"files": validation_details},
                retryable=False,
            ),
        )

    duplicate_details: list[dict[str, object]] = []
    uploads_by_checksum: dict[str, list[dict[str, object]]] = {}
    for upload_data in prepared_uploads:
        checksum = str(upload_data["checksum"])
        uploads_by_checksum.setdefault(checksum, []).append(upload_data)

    for checksum, uploads_for_checksum in uploads_by_checksum.items():
        if len(uploads_for_checksum) > 1:
            for upload_data in uploads_for_checksum:
                duplicate_details.append(
                    {
                        "filename": str(upload_data["filename"]),
                        "checksum": checksum,
                        "reason": "duplicate_in_request",
                    }
                )

    checksums = list(uploads_by_checksum.keys())
    if checksums:
        existing_documents = (
            db.query(Document.id, Document.checksum)
            .filter(Document.checksum.in_(checksums))
            .all()
        )
    else:
        existing_documents = []

    existing_by_checksum = {str(checksum): str(document_id) for document_id, checksum in existing_documents}
    for upload_data in prepared_uploads:
        checksum = str(upload_data["checksum"])
        existing_document_id = existing_by_checksum.get(checksum)
        if existing_document_id:
            duplicate_details.append(
                {
                    "filename": str(upload_data["filename"]),
                    "checksum": checksum,
                    "reason": "already_exists",
                    "document_id": existing_document_id,
                }
            )

    if duplicate_details:
        return JSONResponse(
            status_code=409,
            content=error_envelope(
                request,
                code="DUPLICATE_DOCUMENT",
                message="One or more files already exist.",
                details={"duplicates": duplicate_details},
                retryable=False,
            ),
        )

    for upload_data in prepared_uploads:
        document_id = str(uuid4())
        job_id = str(uuid4())
        content = upload_data["content"]
        checksum = str(upload_data["checksum"])
        storage_uri = storage_backend.store_document(document_id, str(upload_data["filename"]), content)

        document = Document(
            id=document_id,
            team_id=team_id,
            uploaded_by=uploaded_by,
            filename=str(upload_data["filename"]),
            mime_type=str(upload_data["mime_type"]),
            checksum=checksum,
            storage_uri=storage_uri,
            page_count=int(upload_data["page_count"]),
        )
        job = Job(
            id=job_id,
            document_id=document_id,
            status="queued",
        )

        db.add(document)
        db.add(job)
        document_ids.append(document_id)
        job_ids.append(job_id)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=409,
            content=error_envelope(
                request,
                code="DUPLICATE_DOCUMENT",
                message="One or more files already exist.",
                details=None,
                retryable=False,
            ),
        )

    for job_id in job_ids:
        enqueue_processing_job(job_id, request_id=worker_request_id)

    return success_envelope(
        request,
        data={
            "document_ids": document_ids,
            "job_ids": job_ids,
        },
    )
