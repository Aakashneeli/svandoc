"""Job lifecycle state machine and transition helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from svandoc_backend.models.job import Job


ALLOWED_JOB_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"processing", "failed"},
    "processing": {"review_required", "completed", "failed"},
    "review_required": {"processing", "completed", "failed"},
    "failed": {"queued"},
    "completed": set(),
}


class InvalidJobTransitionError(ValueError):
    """Raised when a job transition violates lifecycle rules."""


def can_transition(current_status: str, next_status: str) -> bool:
    if current_status == next_status:
        return True
    return next_status in ALLOWED_JOB_STATUS_TRANSITIONS.get(current_status, set())


def transition_job_status(
    job: Job,
    new_status: str,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    current_status = str(job.status)
    if current_status == new_status:
        return

    if not can_transition(current_status, new_status):
        raise InvalidJobTransitionError(f"Invalid job status transition: {current_status} -> {new_status}")

    now = datetime.now(timezone.utc)

    if new_status == "queued":
        job.started_at = None
        job.finished_at = None
        job.error_code = None
        job.error_message = None

    if new_status == "processing":
        if job.started_at is None:
            job.started_at = now
        job.finished_at = None
        job.attempt_count = int(job.attempt_count) + 1
        job.error_code = None
        job.error_message = None

    if new_status == "review_required":
        job.finished_at = None
        job.error_code = None
        job.error_message = None

    if new_status == "completed":
        job.finished_at = now
        job.error_code = None
        job.error_message = None

    if new_status == "failed":
        job.finished_at = now
        job.error_code = error_code
        job.error_message = error_message

    job.status = new_status
