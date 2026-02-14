"""Redis + Celery integration for asynchronous job processing."""

from __future__ import annotations

import os

from celery import Celery
from sqlalchemy.orm import Session, sessionmaker

from svandoc_backend.db import SessionLocal
from svandoc_backend.job_state_machine import can_transition, transition_job_status
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
    session = JOB_SESSION_FACTORY()
    try:
        job = session.get(Job, job_id)
        if job is None:
            return {"job_id": job_id, "status": "missing"}

        transition_job_status(job, "processing")
        session.commit()

        # Placeholder processing until OCR pipeline tasks are implemented.
        transition_job_status(job, "completed")
        session.commit()
        return {"job_id": job_id, "status": "completed"}
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
        raise
    finally:
        session.close()


def enqueue_processing_job(job_id: str) -> str | None:
    if queue_backend_mode() == "disabled":
        return None

    async_result = process_document_job.delay(job_id)
    return async_result.id
