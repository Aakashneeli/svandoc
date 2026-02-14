"""FastAPI application bootstrap for svanDoc backend."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from svandoc_backend import __version__
from svandoc_backend.db import get_db_session
from svandoc_backend.envelope import error_envelope, success_envelope
from svandoc_backend.models.document import Document
from svandoc_backend.models.job import Job
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
async def ready(request: Request) -> dict[str, object]:
    return success_envelope(
        request,
        data={
            "service": "svandoc-backend",
            "status": "ready",
            "checks": {
                "api": "ok",
            },
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

    for upload_data in prepared_uploads:
        document_id = str(uuid4())
        job_id = str(uuid4())
        content = upload_data["content"]
        checksum = compute_checksum(content)
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

    db.commit()

    return success_envelope(
        request,
        data={
            "document_ids": document_ids,
            "job_ids": job_ids,
        },
    )
