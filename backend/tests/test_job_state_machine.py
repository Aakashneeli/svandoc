import unittest
from dataclasses import dataclass
from datetime import datetime, timezone

from svandoc_backend.job_state_machine import (
    InvalidJobTransitionError,
    can_transition,
    transition_job_status,
)


@dataclass
class JobStub:
    status: str
    attempt_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobStateMachineTests(unittest.TestCase):
    def test_can_transition_accepts_configured_paths(self) -> None:
        self.assertTrue(can_transition("queued", "processing"))
        self.assertTrue(can_transition("processing", "review_required"))
        self.assertTrue(can_transition("review_required", "completed"))
        self.assertTrue(can_transition("failed", "queued"))

    def test_can_transition_rejects_invalid_paths(self) -> None:
        self.assertFalse(can_transition("queued", "completed"))
        self.assertFalse(can_transition("completed", "processing"))

    def test_transition_updates_attempts_and_timestamps(self) -> None:
        job = JobStub(status="queued")
        transition_job_status(job, "processing")
        self.assertEqual(job.status, "processing")
        self.assertEqual(job.attempt_count, 1)
        self.assertIsNotNone(job.started_at)
        self.assertIsNone(job.finished_at)

        transition_job_status(job, "completed")
        self.assertEqual(job.status, "completed")
        self.assertIsNotNone(job.finished_at)

    def test_transition_to_failed_sets_error_fields(self) -> None:
        job = JobStub(status="processing", started_at=datetime.now(timezone.utc))
        transition_job_status(
            job,
            "failed",
            error_code="PROCESSING_ERROR",
            error_message="boom",
        )
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "PROCESSING_ERROR")
        self.assertEqual(job.error_message, "boom")
        self.assertIsNotNone(job.finished_at)

    def test_invalid_transition_raises(self) -> None:
        job = JobStub(status="completed")
        with self.assertRaises(InvalidJobTransitionError):
            transition_job_status(job, "processing")


if __name__ == "__main__":
    unittest.main()
