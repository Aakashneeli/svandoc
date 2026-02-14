"""FastAPI application bootstrap for svanDoc backend."""

from __future__ import annotations

from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from svandoc_backend import __version__
from svandoc_backend.db import get_db_session
from svandoc_backend.envelope import success_envelope
from svandoc_backend.models.document import Document
from svandoc_backend.models.job import Job
from svandoc_backend.uploads import compute_checksum, estimate_page_count, persist_local_file

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

    document_ids: list[str] = []
    job_ids: list[str] = []
    team_id = request.headers.get("x-team-id", "local-team")
    uploaded_by = request.headers.get("x-user-id", "local-user")

    for upload in files:
        content = await upload.read()
        document_id = str(uuid4())
        job_id = str(uuid4())
        checksum = compute_checksum(content)
        page_count = estimate_page_count(content, upload.content_type or "application/octet-stream")
        storage_uri = persist_local_file(document_id, upload.filename, content)

        document = Document(
            id=document_id,
            team_id=team_id,
            uploaded_by=uploaded_by,
            filename=upload.filename or "upload.bin",
            mime_type=upload.content_type or "application/octet-stream",
            checksum=checksum,
            storage_uri=storage_uri,
            page_count=page_count,
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
