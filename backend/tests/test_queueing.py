import os
import shutil
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base
from svandoc_backend.models.document import Document
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job
from svandoc_backend.ocr_types import OCRExtractionResult
from svandoc_backend.queueing import JOB_SESSION_FACTORY, celery_app, enqueue_processing_job, process_document_job
import svandoc_backend.queueing as queueing


class QueueingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"queueing-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "queue-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        self.previous_task_always_eager = bool(celery_app.conf.task_always_eager)
        self.previous_job_session_factory = JOB_SESSION_FACTORY

        queueing.JOB_SESSION_FACTORY = self.SessionTesting
        celery_app.conf.task_always_eager = True

    def tearDown(self) -> None:
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend

        queueing.JOB_SESSION_FACTORY = self.previous_job_session_factory
        celery_app.conf.task_always_eager = self.previous_task_always_eager

        self.engine.dispose()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_document_and_job(self, job_id: str) -> None:
        document_path = self.test_dir / "invoice.pdf"
        document_path.write_bytes(b"%PDF-1.4 test document bytes")
        session = self.SessionTesting()
        try:
            document = Document(
                id="doc-1",
                team_id="team-a",
                uploaded_by="user-a",
                filename="invoice.pdf",
                mime_type="application/pdf",
                checksum="checksum-1",
                storage_uri=str(document_path),
                page_count=1,
            )
            job = Job(
                id=job_id,
                document_id=document.id,
                status="queued",
            )
            session.add(document)
            session.add(job)
            session.commit()
        finally:
            session.close()

    def test_enqueue_processing_job_returns_none_when_queue_disabled(self) -> None:
        os.environ["QUEUE_BACKEND"] = "disabled"
        task_id = enqueue_processing_job("job-1")
        self.assertIsNone(task_id)

    def test_enqueue_processing_job_processes_job_in_eager_mode(self) -> None:
        os.environ["QUEUE_BACKEND"] = "celery"
        job_id = "job-eager-1"
        self._insert_document_and_job(job_id)

        with ExitStack() as stack:
            log_mock = stack.enter_context(patch("svandoc_backend.queueing.emit_worker_log"))
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_from_env",
                    return_value=object(),
                )
            )
            extract_mock = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            extract_mock.return_value = OCRExtractionResult(
                model="dots.ocr",
                raw_text="ACME INVOICE",
                structured_payload={"vendor_name": "ACME"},
                confidence_map={"vendor_name": 0.98},
                review_required=False,
            )
            task_id = enqueue_processing_job(job_id, request_id="req-queue-test")

        self.assertIsInstance(task_id, str)
        self.assertTrue(task_id)
        session = self.SessionTesting()
        try:
            job = session.get(Job, job_id)
            extraction = (
                session.query(ExtractionResult).filter(ExtractionResult.document_id == "doc-1").one_or_none()
            )
        finally:
            session.close()

        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.attempt_count, 1)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNotNone(extraction)
        assert extraction is not None
        self.assertEqual(extraction.raw_ocr_text, "ACME INVOICE")
        self.assertFalse(extraction.is_review_required)
        self.assertGreaterEqual(log_mock.call_count, 2)
        for call in log_mock.call_args_list:
            kwargs = call.kwargs
            self.assertIn("request_id", kwargs)
            self.assertIn("job_id", kwargs)
            self.assertIn("document_id", kwargs)
        self.assertTrue(
            any(
                call.kwargs["request_id"] == "req-queue-test"
                and call.kwargs["job_id"] == job_id
                and call.kwargs["document_id"] == "doc-1"
                and call.kwargs["status"] in {"processing", "completed"}
                for call in log_mock.call_args_list
            )
        )

    def test_process_document_job_returns_missing_for_unknown_job(self) -> None:
        with patch("svandoc_backend.queueing.emit_worker_log") as log_mock:
            result = process_document_job("missing-job-id", request_id="req-missing")
        self.assertEqual(result["status"], "missing")
        log_mock.assert_called_once()
        kwargs = log_mock.call_args.kwargs
        self.assertEqual(kwargs["request_id"], "req-missing")
        self.assertEqual(kwargs["job_id"], "missing-job-id")
        self.assertEqual(kwargs["document_id"], "unknown")

    def test_process_document_job_sets_review_required_when_confidence_is_low(self) -> None:
        job_id = "job-review-required"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_from_env",
                    return_value=object(),
                )
            )
            extract_mock = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            extract_mock.return_value = OCRExtractionResult(
                model="dots.ocr",
                raw_text="LOW CONFIDENCE",
                structured_payload={"vendor_name": "Maybe"},
                confidence_map={"vendor_name": 0.52},
                review_required=True,
            )

            result = process_document_job(job_id, request_id="req-review")

        self.assertEqual(result["status"], "review_required")
        session = self.SessionTesting()
        try:
            job = session.get(Job, job_id)
        finally:
            session.close()
        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.status, "review_required")


if __name__ == "__main__":
    unittest.main()
