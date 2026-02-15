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


class RetryScheduledError(Exception):
    pass


class FakeRetryContext:
    def __init__(self, retries: int) -> None:
        self.request = type("Request", (), {"retries": retries})()
        self.retry_calls: list[dict[str, object]] = []

    def retry(self, *, exc: Exception, countdown: int) -> None:
        self.retry_calls.append({"exc": exc, "countdown": countdown})
        raise RetryScheduledError("retry scheduled")


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
        self.previous_ocr_default_model = os.environ.get("OCR_DEFAULT_MODEL")
        self.previous_ocr_fallback_model = os.environ.get("OCR_FALLBACK_MODEL")
        self.previous_fallback_page_threshold = os.environ.get("OCR_FALLBACK_PAGE_COUNT_THRESHOLD")
        self.previous_processing_max_retries = os.environ.get("PROCESSING_MAX_RETRIES")
        self.previous_task_always_eager = bool(celery_app.conf.task_always_eager)
        self.previous_job_session_factory = JOB_SESSION_FACTORY

        queueing.JOB_SESSION_FACTORY = self.SessionTesting
        celery_app.conf.task_always_eager = True

    def tearDown(self) -> None:
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend
        if self.previous_ocr_default_model is None:
            os.environ.pop("OCR_DEFAULT_MODEL", None)
        else:
            os.environ["OCR_DEFAULT_MODEL"] = self.previous_ocr_default_model
        if self.previous_ocr_fallback_model is None:
            os.environ.pop("OCR_FALLBACK_MODEL", None)
        else:
            os.environ["OCR_FALLBACK_MODEL"] = self.previous_ocr_fallback_model
        if self.previous_fallback_page_threshold is None:
            os.environ.pop("OCR_FALLBACK_PAGE_COUNT_THRESHOLD", None)
        else:
            os.environ["OCR_FALLBACK_PAGE_COUNT_THRESHOLD"] = self.previous_fallback_page_threshold
        if self.previous_processing_max_retries is None:
            os.environ.pop("PROCESSING_MAX_RETRIES", None)
        else:
            os.environ["PROCESSING_MAX_RETRIES"] = self.previous_processing_max_retries

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
                    "svandoc_backend.queueing.build_vllm_client_for_model",
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
        self.assertEqual(extraction.schema_version, "1.0.0")
        self.assertEqual(extraction.doc_type, "invoice")
        self.assertIn("schema_version", extraction.structured_payload)
        self.assertEqual(extraction.structured_payload["schema_version"], "1.0.0")
        self.assertIn("confidence", extraction.structured_payload)
        self.assertEqual(extraction.confidence_map, extraction.structured_payload["confidence"])
        self.assertIn("warnings", extraction.structured_payload)
        self.assertEqual(extraction.structured_payload.get("review_required"), extraction.is_review_required)
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
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "rednote-hilab/dots.ocr"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
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

    def test_process_document_job_can_use_chandra_fallback_adapter(self) -> None:
        job_id = "job-chandra-fallback"
        os.environ["OCR_DEFAULT_MODEL"] = "chandra"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
                    return_value=object(),
                )
            )
            dots_extract = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            chandra_extract = stack.enter_context(patch("svandoc_backend.queueing.ChandraOCRAdapter.extract"))
            chandra_extract.return_value = OCRExtractionResult(
                model="chandra",
                raw_text="CHANDRA RAW",
                structured_payload={
                    "line_items": [{"description": "Part A", "qty": 2, "unit_price": 20.0, "amount": 40.0}]
                },
                confidence_map={"line_items": [{"description": 0.9, "amount": 0.87}]},
                review_required=False,
            )

            result = process_document_job(job_id, request_id="req-chandra")

        self.assertEqual(result["status"], "completed")
        self.assertFalse(dots_extract.called)
        self.assertTrue(chandra_extract.called)

    def test_process_document_job_routes_from_dots_to_chandra_when_review_required(self) -> None:
        job_id = "job-route-review-required"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        os.environ["OCR_FALLBACK_PAGE_COUNT_THRESHOLD"] = "10"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
                    side_effect=[object(), object()],
                )
            )
            dots_extract = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            chandra_extract = stack.enter_context(patch("svandoc_backend.queueing.ChandraOCRAdapter.extract"))
            dots_extract.return_value = OCRExtractionResult(
                model="rednote-hilab/dots.ocr",
                raw_text="DOTS LOW",
                structured_payload={"vendor_name": "ACME"},
                confidence_map={"vendor_name": 0.62},
                review_required=True,
            )
            chandra_extract.return_value = OCRExtractionResult(
                model="datalab-to/chandra",
                raw_text="CHANDRA BETTER",
                structured_payload={"vendor_name": "ACME Ltd"},
                confidence_map={"vendor_name": 0.95},
                review_required=False,
            )
            result = process_document_job(job_id, request_id="req-route-review")

        self.assertEqual(result["status"], "completed")
        self.assertTrue(dots_extract.called)
        self.assertTrue(chandra_extract.called)

        session = self.SessionTesting()
        try:
            extraction = (
                session.query(ExtractionResult).filter(ExtractionResult.document_id == "doc-1").one_or_none()
            )
        finally:
            session.close()
        self.assertIsNotNone(extraction)
        assert extraction is not None
        self.assertEqual(extraction.raw_ocr_text, "CHANDRA BETTER")
        self.assertFalse(extraction.is_review_required)

    def test_process_document_job_does_not_route_when_primary_is_confident(self) -> None:
        job_id = "job-no-route"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        os.environ["OCR_FALLBACK_PAGE_COUNT_THRESHOLD"] = "10"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
                    return_value=object(),
                )
            )
            dots_extract = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            chandra_extract = stack.enter_context(patch("svandoc_backend.queueing.ChandraOCRAdapter.extract"))
            dots_extract.return_value = OCRExtractionResult(
                model="rednote-hilab/dots.ocr",
                raw_text="DOTS CONFIDENT",
                structured_payload={"vendor_name": "ACME"},
                confidence_map={"vendor_name": 0.96, "total": 0.95},
                review_required=False,
            )
            result = process_document_job(job_id, request_id="req-no-route")

        self.assertEqual(result["status"], "completed")
        self.assertTrue(dots_extract.called)
        self.assertFalse(chandra_extract.called)

    def test_process_document_job_marks_review_required_when_validation_fails(self) -> None:
        job_id = "job-validation-review"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "rednote-hilab/dots.ocr"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
                    return_value=object(),
                )
            )
            dots_extract = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            dots_extract.return_value = OCRExtractionResult(
                model="rednote-hilab/dots.ocr",
                raw_text="INVOICE INVALID TOTAL",
                structured_payload={
                    "vendor_name": "ACME",
                    "invoice_number": "INV-7",
                    "issue_date": "2026-02-15",
                    "currency": "USD",
                    "subtotal": 100.0,
                    "tax": 10.0,
                    "shipping": 0.0,
                    "discount": 0.0,
                    "total": 50.0,
                },
                confidence_map={"vendor_name": 0.95, "total": 0.94},
                review_required=False,
            )
            result = process_document_job(job_id, request_id="req-validation-review")

        self.assertEqual(result["status"], "review_required")
        session = self.SessionTesting()
        try:
            extraction = (
                session.query(ExtractionResult).filter(ExtractionResult.document_id == "doc-1").one_or_none()
            )
            job = session.get(Job, job_id)
        finally:
            session.close()
        self.assertIsNotNone(extraction)
        assert extraction is not None
        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(extraction.schema_version, "1.0.0")
        self.assertEqual(extraction.confidence_map, extraction.structured_payload["confidence"])
        self.assertEqual(extraction.structured_payload.get("review_required"), extraction.is_review_required)
        self.assertTrue(extraction.is_review_required)
        warnings = extraction.structured_payload.get("warnings")
        self.assertIsInstance(warnings, list)
        self.assertTrue(any("amounts.total mismatch for invoice" in str(item) for item in warnings))
        self.assertEqual(job.status, "review_required")

    def test_process_document_job_marks_failed_when_client_selection_errors(self) -> None:
        job_id = "job-fallback-client-error"
        os.environ["OCR_DEFAULT_MODEL"] = "datalab-to/chandra"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        self._insert_document_and_job(job_id)

        with self.assertRaises(RuntimeError):
            with patch(
                "svandoc_backend.queueing.build_vllm_client_for_model",
                side_effect=RuntimeError("fallback endpoint unavailable"),
            ):
                process_document_job(job_id, request_id="req-fallback-error")

        session = self.SessionTesting()
        try:
            job = session.get(Job, job_id)
        finally:
            session.close()
        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "PROCESSING_ERROR")
        self.assertIn("fallback endpoint unavailable", str(job.error_message))

    def test_process_document_job_schedules_retry_for_retryable_errors(self) -> None:
        job_id = "job-retryable-error"
        os.environ["PROCESSING_MAX_RETRIES"] = "3"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        self._insert_document_and_job(job_id)
        retry_context = FakeRetryContext(retries=0)

        with self.assertRaises(RetryScheduledError):
            with patch(
                "svandoc_backend.queueing.build_vllm_client_for_model",
                side_effect=TimeoutError("temporary inference timeout"),
            ):
                process_document_job(job_id, request_id="req-retryable", retry_context=retry_context)

        self.assertEqual(len(retry_context.retry_calls), 1)
        self.assertGreaterEqual(int(retry_context.retry_calls[0]["countdown"]), 1)

        session = self.SessionTesting()
        try:
            job = session.get(Job, job_id)
        finally:
            session.close()

        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.status, "queued")
        self.assertEqual(job.attempt_count, 1)
        self.assertIsNone(job.error_code)
        self.assertIsNone(job.error_message)

    def test_process_document_job_marks_dead_letter_when_retries_exhausted(self) -> None:
        job_id = "job-dead-letter"
        os.environ["PROCESSING_MAX_RETRIES"] = "1"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        self._insert_document_and_job(job_id)
        retry_context = FakeRetryContext(retries=0)

        with self.assertRaises(TimeoutError):
            with patch(
                "svandoc_backend.queueing.build_vllm_client_for_model",
                side_effect=TimeoutError("temporary inference timeout"),
            ):
                process_document_job(job_id, request_id="req-dead-letter", retry_context=retry_context)

        self.assertEqual(len(retry_context.retry_calls), 0)

        session = self.SessionTesting()
        try:
            job = session.get(Job, job_id)
        finally:
            session.close()

        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "DEAD_LETTER")
        self.assertIn("temporary inference timeout", str(job.error_message))

    def test_process_document_job_emits_completed_webhook_event(self) -> None:
        job_id = "job-webhook-completed"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        os.environ["OCR_FALLBACK_PAGE_COUNT_THRESHOLD"] = "10"
        self._insert_document_and_job(job_id)
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
                    return_value=object(),
                )
            )
            dots_extract = stack.enter_context(patch("svandoc_backend.queueing.DotsOCRAdapter.extract"))
            webhook_mock = stack.enter_context(patch("svandoc_backend.queueing.deliver_webhook_event"))
            dots_extract.return_value = OCRExtractionResult(
                model="rednote-hilab/dots.ocr",
                raw_text="DOTS CONFIDENT",
                structured_payload={"vendor_name": "ACME"},
                confidence_map={"vendor_name": 0.96, "total": 0.95},
                review_required=False,
            )
            process_document_job(job_id, request_id="req-webhook-completed")

        webhook_mock.assert_called_once()
        _, kwargs = webhook_mock.call_args
        self.assertEqual(kwargs["event_type"], "job.completed")
        self.assertEqual(kwargs["data"]["job_id"], job_id)

    def test_process_document_job_emits_failed_webhook_event(self) -> None:
        job_id = "job-webhook-failed"
        os.environ["OCR_DEFAULT_MODEL"] = "rednote-hilab/dots.ocr"
        os.environ["OCR_FALLBACK_MODEL"] = "datalab-to/chandra"
        self._insert_document_and_job(job_id)
        with patch("svandoc_backend.queueing.deliver_webhook_event") as webhook_mock:
            with self.assertRaises(RuntimeError):
                with patch(
                    "svandoc_backend.queueing.build_vllm_client_for_model",
                    side_effect=RuntimeError("inference unavailable"),
                ):
                    process_document_job(job_id, request_id="req-webhook-failed")

        webhook_mock.assert_called_once()
        _, kwargs = webhook_mock.call_args
        self.assertEqual(kwargs["event_type"], "job.failed")
        self.assertEqual(kwargs["data"]["job_id"], job_id)


if __name__ == "__main__":
    unittest.main()
