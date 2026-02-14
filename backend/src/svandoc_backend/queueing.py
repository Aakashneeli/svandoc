"""Redis + Celery integration for asynchronous job processing."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy.orm import Session, sessionmaker

from svandoc_backend.db import SessionLocal
from svandoc_backend.models.job import Job

DEFAULT_REDIS_URL = "redis://localhost:6379/0"

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
def process_document_job(job_id: str) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    session = JOB_SESSION_FACTORY()
    try:
        job = session.get(Job, job_id)
        if job is None:
            return {"job_id": job_id, "status": "missing"}

        job.status = "processing"
        job.started_at = now
        session.commit()

        # Placeholder processing until OCR pipeline tasks are implemented.
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.error_code = None
        job.error_message = None
        session.commit()
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:  # pragma: no cover - defensive path
        session.rollback()
        failed_job = session.get(Job, job_id)
        if failed_job is not None:
            failed_job.status = "failed"
            failed_job.error_code = "PROCESSING_ERROR"
            failed_job.error_message = str(exc)
            failed_job.finished_at = datetime.now(timezone.utc)
            session.commit()
        raise
    finally:
        session.close()


def enqueue_processing_job(job_id: str) -> str | None:
    if queue_backend_mode() == "disabled":
        return None

    async_result = process_document_job.delay(job_id)
    return async_result.id
