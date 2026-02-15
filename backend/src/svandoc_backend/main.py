"""FastAPI application bootstrap for svanDoc backend."""

from __future__ import annotations

import json
import hashlib
import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from sqlalchemy.orm import Session

from svandoc_backend import __version__
from svandoc_backend.alerts import evaluate_alerts
from svandoc_backend.auth import require_roles
from svandoc_backend.cloud_connectors import (
    CloudConnectorError,
    upload_to_dropbox,
    upload_to_google_drive,
    upload_to_onedrive,
)
from svandoc_backend.db import get_db_session
from svandoc_backend.envelope import error_envelope, request_id_from_request, success_envelope
from svandoc_backend.export_service import (
    build_csv_export,
    build_json_export,
    build_tabular_export_row,
    build_xlsx_export,
)
from svandoc_backend.google_sheets_export import GoogleSheetsExportError, append_to_google_sheet
from svandoc_backend.logging_sink import configure_structured_logging
from svandoc_backend.make_templates import build_make_templates
from svandoc_backend.metrics import metrics_snapshot, record_api_request
from svandoc_backend.models.document import Document
from svandoc_backend.models.export_artifact import ExportArtifact
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job
from svandoc_backend.models.user_correction import UserCorrection
from svandoc_backend.models.xero_sync_log import XeroSyncLog
from svandoc_backend.queueing import enqueue_processing_job
from svandoc_backend.quickbooks_connector import QuickBooksConnectorError, export_to_quickbooks
from svandoc_backend.rate_limit import rate_limiter, rate_limit_subject, should_rate_limit_path
from svandoc_backend.sage_connector import build_sage_export_plan
from svandoc_backend.storage import get_storage_backend
from svandoc_backend.tally_connector import build_tally_import_package
from svandoc_backend.uploads import (
    compute_checksum,
    normalized_mime_type,
    safe_filename,
    validate_upload,
)
from svandoc_backend.webhooks import deliver_webhook_event
from svandoc_backend.xero_connector import XeroConnectorError, XeroSyncAttempt, export_to_xero

app = FastAPI(
    title="svanDoc Backend API",
    version=__version__,
)
configure_structured_logging()
api_logger = logging.getLogger("svandoc.api")


@app.middleware("http")
async def add_request_correlation(request: Request, call_next):
    request_id = request.headers.get("x-request-id", "").strip() or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    started = perf_counter()

    if should_rate_limit_path(request.url.path):
        subject = rate_limit_subject(request)
        decision = rate_limiter.evaluate(subject, request.url.path)
        if not decision.allowed:
            record_api_request(duration_ms=0, status_code=429)
            response = JSONResponse(
                status_code=429,
                content=error_envelope(
                    request,
                    code=decision.code or "RATE_LIMITED",
                    message="Too many requests. Please retry later.",
                    details={
                        "reason": decision.reason,
                        "retry_after_seconds": decision.retry_after_seconds,
                        "subject": subject,
                    },
                    retryable=True,
                ),
            )
            response.headers["x-request-id"] = request_id
            if decision.retry_after_seconds is not None:
                response.headers["Retry-After"] = str(decision.retry_after_seconds)
            api_logger.info(
                json.dumps(
                    {
                        "event": "request_rate_limited",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "subject": subject,
                        "reason": decision.reason,
                        "retry_after_seconds": decision.retry_after_seconds,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            return response

    api_logger.info(
        json.dumps(
            {
                "event": "request_started",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        record_api_request(duration_ms=duration_ms, status_code=500)
        api_logger.info(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        raise

    duration_ms = int((perf_counter() - started) * 1000)
    record_api_request(duration_ms=duration_ms, status_code=response.status_code)
    response.headers["x-request-id"] = request_id
    api_logger.info(
        json.dumps(
            {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return response


@app.get("/metrics")
async def metrics(request: Request) -> dict[str, object]:
    snapshot = metrics_snapshot()
    return success_envelope(
        request,
        data={
            **snapshot,
            "alerts": evaluate_alerts(snapshot),
        },
    )


@app.get("/alerts")
async def alerts(request: Request) -> dict[str, object]:
    snapshot = metrics_snapshot()
    return success_envelope(
        request,
        data=evaluate_alerts(snapshot),
    )


class CorrectionInput(BaseModel):
    field_path: str = Field(..., min_length=1)
    new_value: Any


class ExtractionCorrectionRequest(BaseModel):
    corrections: list[CorrectionInput] = Field(..., min_length=1)


class ExportRequest(BaseModel):
    format: str = Field(..., min_length=1)
    google_spreadsheet_id: str | None = None
    google_sheet_name: str | None = None
    google_access_token: str | None = None
    cloud_access_token: str | None = None
    cloud_folder: str | None = None
    cloud_filename: str | None = None
    quickbooks_access_token: str | None = None
    quickbooks_realm_id: str | None = None
    xero_access_token: str | None = None
    xero_tenant_id: str | None = None


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


def _xero_idempotency_key(document_id: str, payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    raw = f"{document_id}:{serialized}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:64]


def _persist_xero_sync_logs(
    db: Session,
    *,
    artifact_id: str,
    document_id: str,
    idempotency_key: str,
    attempts: list[XeroSyncAttempt],
) -> None:
    for attempt in attempts:
        db.add(
            XeroSyncLog(
                id=str(uuid4()),
                artifact_id=artifact_id,
                document_id=document_id,
                idempotency_key=idempotency_key,
                attempt_number=int(attempt.attempt_number),
                sync_status=str(attempt.sync_status),
                external_reference=attempt.external_reference,
                error_message=attempt.error_message,
            )
        )


def _parse_iso_datetime(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def require_zapier_key(request: Request) -> JSONResponse | None:
    configured = os.getenv("ZAPIER_API_KEY", "").strip()
    if not configured:
        return JSONResponse(
            status_code=503,
            content=error_envelope(
                request,
                code="CONFIGURATION_ERROR",
                message="Zapier integration is not configured.",
                details={"missing_env": ["ZAPIER_API_KEY"]},
                retryable=False,
            ),
        )

    received = request.headers.get("x-zapier-api-key", "").strip()
    if not received or received != configured:
        return JSONResponse(
            status_code=403,
            content=error_envelope(
                request,
                code="FORBIDDEN",
                message="Invalid Zapier API key.",
                details=None,
                retryable=False,
            ),
        )
    return None


def require_make_key(request: Request) -> JSONResponse | None:
    configured = os.getenv("MAKE_API_KEY", "").strip()
    if not configured:
        return JSONResponse(
            status_code=503,
            content=error_envelope(
                request,
                code="CONFIGURATION_ERROR",
                message="Make integration is not configured.",
                details={"missing_env": ["MAKE_API_KEY"]},
                retryable=False,
            ),
        )

    received = request.headers.get("x-make-api-key", "").strip()
    if not received or received != configured:
        return JSONResponse(
            status_code=403,
            content=error_envelope(
                request,
                code="FORBIDDEN",
                message="Invalid Make API key.",
                details=None,
                retryable=False,
            ),
        )
    return None


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
    auth_error = require_roles(request, {"admin", "editor", "viewer"})
    if auth_error is not None:
        return auth_error

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
    auth_error = require_roles(request, {"admin", "editor", "viewer"})
    if auth_error is not None:
        return auth_error

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


@app.get("/api/documents/{document_id}/audit")
async def get_document_audit_log(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    auth_error = require_roles(request, {"admin", "editor", "viewer"})
    if auth_error is not None:
        return auth_error

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

    corrections = (
        db.query(UserCorrection)
        .filter(UserCorrection.document_id == document_id)
        .order_by(UserCorrection.corrected_at.desc())
        .all()
    )
    exports = (
        db.query(ExportArtifact)
        .filter(ExportArtifact.document_id == document_id)
        .order_by(ExportArtifact.created_at.desc())
        .all()
    )

    return success_envelope(
        request,
        data={
            "document_id": document_id,
            "corrections": [
                {
                    "id": str(correction.id),
                    "field_path": str(correction.field_path),
                    "old_value": correction.old_value,
                    "new_value": correction.new_value,
                    "corrected_by": str(correction.corrected_by),
                    "corrected_at": _iso_timestamp(correction.corrected_at),
                }
                for correction in corrections
            ],
            "exports": [
                {
                    "id": str(artifact.id),
                    "format": str(artifact.format),
                    "storage_uri": str(artifact.storage_uri),
                    "delivery_status": str(artifact.delivery_status),
                    "created_by": str(artifact.created_by),
                    "created_at": _iso_timestamp(artifact.created_at),
                }
                for artifact in exports
            ],
        },
    )


@app.get("/api/integrations/zapier/triggers/job-completed")
async def zapier_trigger_job_completed(
    request: Request,
    since: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    auth_error = require_zapier_key(request)
    if auth_error is not None:
        return auth_error

    query = db.query(Job).filter(Job.status == "completed")
    if since:
        try:
            since_timestamp = _parse_iso_datetime(since)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content=error_envelope(
                    request,
                    code="VALIDATION_ERROR",
                    message="Invalid 'since' timestamp format.",
                    details={"since": since},
                    retryable=False,
                ),
            )
        query = query.filter(Job.finished_at >= since_timestamp)

    jobs = query.order_by(Job.finished_at.desc()).limit(limit).all()
    return success_envelope(
        request,
        data={
            "jobs": [
                {
                    "job_id": str(job.id),
                    "document_id": str(job.document_id),
                    "status": str(job.status),
                    "attempt_count": int(job.attempt_count),
                    "finished_at": _iso_timestamp(job.finished_at),
                }
                for job in jobs
            ]
        },
    )


@app.get("/api/integrations/zapier/actions/fetch-results")
async def zapier_action_fetch_results(
    request: Request,
    document_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    auth_error = require_zapier_key(request)
    if auth_error is not None:
        return auth_error

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
            "structured_payload": extraction.structured_payload,
            "confidence_map": extraction.confidence_map,
            "updated_at": _iso_timestamp(extraction.updated_at),
        },
    )


@app.get("/api/integrations/make/templates")
async def make_templates(request: Request) -> dict[str, object]:
    auth_error = require_make_key(request)
    if auth_error is not None:
        return auth_error

    api_base_url = os.getenv("MAKE_API_BASE_URL", "").strip()
    if not api_base_url:
        api_base_url = str(request.base_url).rstrip("/")
    templates = build_make_templates(api_base_url=api_base_url)
    return success_envelope(
        request,
        data={
            "templates": templates,
        },
    )


@app.patch("/api/documents/{document_id}/extraction")
async def patch_document_extraction(
    request: Request,
    document_id: str,
    correction_request: ExtractionCorrectionRequest,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    auth_error = require_roles(request, {"admin", "editor"})
    if auth_error is not None:
        return auth_error

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
    auth_error = require_roles(request, {"admin", "editor", "viewer"})
    if auth_error is not None:
        return auth_error

    export_format = _normalize_export_format(export_request.format)
    supported_formats = [
        "json",
        "csv",
        "xlsx",
        "gsheets",
        "gdrive",
        "onedrive",
        "dropbox",
        "quickbooks",
        "xero",
        "sage",
        "tally",
    ]
    if export_format not in supported_formats:
        return JSONResponse(
            status_code=400,
            content=error_envelope(
                request,
                code="VALIDATION_ERROR",
                message="Unsupported export format.",
                details={"format": export_request.format, "supported_formats": supported_formats},
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

    payload = extraction.structured_payload
    artifact_id = str(uuid4())
    delivery_status = "completed"
    if export_format == "gsheets":
        spreadsheet_id = (export_request.google_spreadsheet_id or "").strip()
        access_token = (export_request.google_access_token or "").strip()
        sheet_name = (export_request.google_sheet_name or "").strip() or "Sheet1"
        missing_fields: list[str] = []
        if not spreadsheet_id:
            missing_fields.append("google_spreadsheet_id")
        if not access_token:
            missing_fields.append("google_access_token")
        if missing_fields:
            return JSONResponse(
                status_code=400,
                content=error_envelope(
                    request,
                    code="VALIDATION_ERROR",
                    message="Google Sheets export requires OAuth token and spreadsheet target.",
                    details={"missing_fields": missing_fields},
                    retryable=False,
                ),
            )
        headers, row = build_tabular_export_row(payload)
        try:
            connector_result = append_to_google_sheet(
                access_token=access_token,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                headers=headers,
                row=row,
            )
        except GoogleSheetsExportError as exc:
            return JSONResponse(
                status_code=502,
                content=error_envelope(
                    request,
                    code="EXPORT_DELIVERY_FAILED",
                    message="Google Sheets export failed.",
                    details={"connector": "google_sheets", "reason": str(exc)},
                    retryable=True,
                ),
            )
        storage_uri = f"gsheets://{connector_result.spreadsheet_id}/{connector_result.sheet_name}"
    elif export_format in {"gdrive", "onedrive", "dropbox"}:
        access_token = (export_request.cloud_access_token or "").strip()
        if not access_token:
            return JSONResponse(
                status_code=400,
                content=error_envelope(
                    request,
                    code="VALIDATION_ERROR",
                    message="Cloud connector export requires OAuth access token.",
                    details={"missing_fields": ["cloud_access_token"]},
                    retryable=False,
                ),
            )
        cloud_filename = (export_request.cloud_filename or "").strip() or f"{document_id}.json"
        cloud_folder = (export_request.cloud_folder or "").strip()
        export_content = build_json_export(payload)
        try:
            if export_format == "gdrive":
                connector_result = upload_to_google_drive(
                    access_token=access_token,
                    filename=cloud_filename,
                    content=export_content,
                    mime_type="application/json",
                    folder_id=cloud_folder or None,
                )
            elif export_format == "onedrive":
                connector_result = upload_to_onedrive(
                    access_token=access_token,
                    filename=cloud_filename,
                    content=export_content,
                    folder_path=cloud_folder or "svandoc-exports",
                )
            else:
                connector_result = upload_to_dropbox(
                    access_token=access_token,
                    filename=cloud_filename,
                    content=export_content,
                    folder_path=cloud_folder or "/svandoc-exports",
                )
        except CloudConnectorError as exc:
            delivery_status = "failed"
            storage_uri = f"failed://{export_format}"
            created_by = request.headers.get("x-user-id", "local-user")
            created_at = datetime.now(timezone.utc)
            db.add(
                ExportArtifact(
                    id=artifact_id,
                    document_id=document_id,
                    format=export_format,
                    storage_uri=storage_uri,
                    delivery_status=delivery_status,
                    created_by=created_by,
                    created_at=created_at,
                )
            )
            db.commit()
            deliver_webhook_event(
                db,
                event_type="export.created",
                data={
                    "artifact_id": artifact_id,
                    "document_id": document_id,
                    "format": export_format,
                    "storage_uri": storage_uri,
                    "delivery_status": delivery_status,
                    "created_by": created_by,
                    "created_at": _iso_timestamp(created_at),
                },
            )
            return JSONResponse(
                status_code=502,
                content=error_envelope(
                    request,
                    code="EXPORT_DELIVERY_FAILED",
                    message="Cloud connector export failed.",
                    details={"connector": export_format, "reason": str(exc), "artifact_id": artifact_id},
                    retryable=True,
                ),
            )
        storage_uri = connector_result.storage_uri
    elif export_format == "quickbooks":
        quickbooks_access_token = (export_request.quickbooks_access_token or "").strip()
        quickbooks_realm_id = (export_request.quickbooks_realm_id or "").strip()
        missing_fields: list[str] = []
        if not quickbooks_access_token:
            missing_fields.append("quickbooks_access_token")
        if not quickbooks_realm_id:
            missing_fields.append("quickbooks_realm_id")
        if missing_fields:
            return JSONResponse(
                status_code=400,
                content=error_envelope(
                    request,
                    code="VALIDATION_ERROR",
                    message="QuickBooks export requires access token and realm ID.",
                    details={"missing_fields": missing_fields},
                    retryable=False,
                ),
            )
        try:
            connector_result = export_to_quickbooks(
                access_token=quickbooks_access_token,
                realm_id=quickbooks_realm_id,
                payload=payload,
                api_base_url=(
                    os.getenv("QUICKBOOKS_API_BASE_URL", "https://quickbooks.api.intuit.com").strip()
                    or "https://quickbooks.api.intuit.com"
                ),
            )
        except QuickBooksConnectorError as exc:
            delivery_status = "failed"
            storage_uri = "failed://quickbooks"
            created_by = request.headers.get("x-user-id", "local-user")
            created_at = datetime.now(timezone.utc)
            db.add(
                ExportArtifact(
                    id=artifact_id,
                    document_id=document_id,
                    format=export_format,
                    storage_uri=storage_uri,
                    delivery_status=delivery_status,
                    created_by=created_by,
                    created_at=created_at,
                )
            )
            db.commit()
            deliver_webhook_event(
                db,
                event_type="export.created",
                data={
                    "artifact_id": artifact_id,
                    "document_id": document_id,
                    "format": export_format,
                    "storage_uri": storage_uri,
                    "delivery_status": delivery_status,
                    "created_by": created_by,
                    "created_at": _iso_timestamp(created_at),
                },
            )
            return JSONResponse(
                status_code=502,
                content=error_envelope(
                    request,
                    code="EXPORT_DELIVERY_FAILED",
                    message="QuickBooks export failed.",
                    details={"connector": "quickbooks", "reason": str(exc), "artifact_id": artifact_id},
                    retryable=True,
                ),
            )
        storage_uri = connector_result.storage_uri
    elif export_format == "xero":
        xero_access_token = (export_request.xero_access_token or "").strip()
        xero_tenant_id = (export_request.xero_tenant_id or "").strip()
        missing_fields: list[str] = []
        if not xero_access_token:
            missing_fields.append("xero_access_token")
        if not xero_tenant_id:
            missing_fields.append("xero_tenant_id")
        if missing_fields:
            return JSONResponse(
                status_code=400,
                content=error_envelope(
                    request,
                    code="VALIDATION_ERROR",
                    message="Xero export requires access token and tenant ID.",
                    details={"missing_fields": missing_fields},
                    retryable=False,
                ),
            )
        idempotency_key = _xero_idempotency_key(document_id, payload)
        try:
            connector_result = export_to_xero(
                access_token=xero_access_token,
                tenant_id=xero_tenant_id,
                payload=payload,
                idempotency_key=idempotency_key,
                api_base_url=(os.getenv("XERO_API_BASE_URL", "https://api.xero.com/api.xro/2.0").strip() or "https://api.xero.com/api.xro/2.0"),
            )
            storage_uri = connector_result.storage_uri
            _persist_xero_sync_logs(
                db,
                artifact_id=artifact_id,
                document_id=document_id,
                idempotency_key=idempotency_key,
                attempts=connector_result.attempts,
            )
        except XeroConnectorError as exc:
            delivery_status = "failed"
            storage_uri = "failed://xero"
            created_by = request.headers.get("x-user-id", "local-user")
            created_at = datetime.now(timezone.utc)
            db.add(
                ExportArtifact(
                    id=artifact_id,
                    document_id=document_id,
                    format=export_format,
                    storage_uri=storage_uri,
                    delivery_status=delivery_status,
                    created_by=created_by,
                    created_at=created_at,
                )
            )
            _persist_xero_sync_logs(
                db,
                artifact_id=artifact_id,
                document_id=document_id,
                idempotency_key=idempotency_key,
                attempts=exc.attempts,
            )
            db.commit()
            deliver_webhook_event(
                db,
                event_type="export.created",
                data={
                    "artifact_id": artifact_id,
                    "document_id": document_id,
                    "format": export_format,
                    "storage_uri": storage_uri,
                    "delivery_status": delivery_status,
                    "created_by": created_by,
                    "created_at": _iso_timestamp(created_at),
                },
            )
            return JSONResponse(
                status_code=502,
                content=error_envelope(
                    request,
                    code="EXPORT_DELIVERY_FAILED",
                    message="Xero export failed.",
                    details={"connector": "xero", "reason": str(exc), "artifact_id": artifact_id},
                    retryable=True,
                ),
            )
    elif export_format == "sage":
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
        plan = build_sage_export_plan(payload)
        export_content = json.dumps(plan.payload, sort_keys=True, indent=2, ensure_ascii=True).encode("utf-8")
        artifact_filename = f"{document_id}.sage-plan.json"
        storage_uri = storage_backend.store_document(artifact_id, artifact_filename, export_content)
    elif export_format == "tally":
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
        package = build_tally_import_package(payload)
        storage_uri = storage_backend.store_document(artifact_id, package.filename, package.content)
    else:
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

        if export_format == "json":
            export_content = build_json_export(payload)
        elif export_format == "csv":
            export_content = build_csv_export(payload)
        else:
            export_content = build_xlsx_export(payload)
        artifact_filename = f"{document_id}.{export_format}"
        storage_uri = storage_backend.store_document(artifact_id, artifact_filename, export_content)
    created_by = request.headers.get("x-user-id", "local-user")
    created_at = datetime.now(timezone.utc)

    artifact = ExportArtifact(
        id=artifact_id,
        document_id=document_id,
        format=export_format,
        storage_uri=storage_uri,
        delivery_status=delivery_status,
        created_by=created_by,
        created_at=created_at,
    )
    db.add(artifact)
    db.commit()
    deliver_webhook_event(
        db,
        event_type="export.created",
        data={
            "artifact_id": artifact_id,
            "document_id": document_id,
            "format": export_format,
            "storage_uri": storage_uri,
            "delivery_status": delivery_status,
            "created_by": created_by,
            "created_at": _iso_timestamp(created_at),
        },
    )

    return success_envelope(
        request,
        data={
            "artifact_id": artifact_id,
            "document_id": document_id,
            "format": export_format,
            "storage_uri": storage_uri,
            "delivery_status": delivery_status,
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
    auth_error = require_roles(request, {"admin", "editor"})
    if auth_error is not None:
        return auth_error

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
