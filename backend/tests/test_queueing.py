import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base
from svandoc_backend.models.document import Document
from svandoc_backend.models.job import Job
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
        session = self.SessionTesting()
        try:
            document = Document(
                id="doc-1",
                team_id="team-a",
                uploaded_by="user-a",
                filename="invoice.pdf",
                mime_type="application/pdf",
                checksum="checksum-1",
                storage_uri="/tmp/invoice.pdf",
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

        task_id = enqueue_processing_job(job_id)

        self.assertIsInstance(task_id, str)
        self.assertTrue(task_id)
        session = self.SessionTesting()
        try:
            job = session.get(Job, job_id)
        finally:
            session.close()

        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.attempt_count, 1)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)

    def test_process_document_job_returns_missing_for_unknown_job(self) -> None:
        result = process_document_job("missing-job-id")
        self.assertEqual(result["status"], "missing")


if __name__ == "__main__":
    unittest.main()
