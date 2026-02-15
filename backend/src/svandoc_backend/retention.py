"""Document retention policy and hard-delete cleanup job."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from svandoc_backend.db import SessionLocal
from svandoc_backend.models.document import Document
from svandoc_backend.models.document_deletion_event import DocumentDeletionEvent

DEFAULT_RETENTION_DAYS = 365


def _read_retention_days() -> int:
    raw = os.getenv("DOCUMENT_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)).strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_RETENTION_DAYS
    return value if value > 0 else DEFAULT_RETENTION_DAYS


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_storage_path(storage_uri: str) -> Path | None:
    if storage_uri.startswith("s3://"):
        path_without_scheme = storage_uri[len("s3://") :]
        bucket_and_path = path_without_scheme.split("/", 1)
        if len(bucket_and_path) != 2:
            return None
        bucket_name, object_path = bucket_and_path
        stub_root = os.getenv("S3_STUB_STORAGE_PATH", "./data/s3-stub").strip() or "./data/s3-stub"
        return Path(stub_root) / bucket_name / object_path
    return Path(storage_uri)


def _delete_storage_object(storage_uri: str) -> bool:
    resolved = _resolve_storage_path(storage_uri)
    if resolved is None:
        return False
    if not resolved.exists():
        return False
    resolved.unlink()
    return True


def hard_delete_expired_documents(
    session: Session,
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
    deleted_by: str = "retention-job",
    delete_reason: str = "retention_policy",
) -> dict[str, Any]:
    effective_now = _coerce_utc(now) if now is not None else _utc_now()
    effective_days = retention_days if retention_days is not None else _read_retention_days()
    cutoff = effective_now - timedelta(days=effective_days)

    expired_documents = session.query(Document).filter(Document.created_at < cutoff).all()
    deleted_count = 0
    deleted_storage_count = 0
    deleted_document_ids: list[str] = []

    for document in expired_documents:
        created_at = _coerce_utc(document.created_at)
        session.add(
            DocumentDeletionEvent(
                id=str(uuid4()),
                document_id=str(document.id),
                team_id=str(document.team_id),
                filename=str(document.filename),
                checksum=str(document.checksum),
                storage_uri=str(document.storage_uri),
                delete_reason=delete_reason,
                deleted_by=deleted_by,
                original_created_at=created_at,
                deleted_at=effective_now,
            )
        )
        if _delete_storage_object(str(document.storage_uri)):
            deleted_storage_count += 1
        deleted_document_ids.append(str(document.id))
        session.delete(document)
        deleted_count += 1

    session.commit()
    return {
        "retention_days": effective_days,
        "cutoff": cutoff.isoformat(),
        "deleted_document_count": deleted_count,
        "deleted_storage_object_count": deleted_storage_count,
        "deleted_document_ids": deleted_document_ids,
    }


def main() -> int:
    session = SessionLocal()
    try:
        result = hard_delete_expired_documents(session)
    finally:
        session.close()

    print(
        "[retention] "
        f"retention_days={result['retention_days']} "
        f"deleted_documents={result['deleted_document_count']} "
        f"deleted_storage_objects={result['deleted_storage_object_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
