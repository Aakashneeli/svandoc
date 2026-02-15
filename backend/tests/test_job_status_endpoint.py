import os
import re
import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base, get_db_session
from svandoc_backend.main import app
from svandoc_backend.models.document import Document
from svandoc_backend.models.job import Job


TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class JobStatusEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"job-status-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "job-status-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        os.environ["QUEUE_BACKEND"] = "disabled"

        def override_db_session():
            session = self.SessionTesting()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_db_session
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_document_and_job(
        self,
        *,
        job_id: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        session = self.SessionTesting()
        try:
            document = Document(
                id="doc-job-1",
                team_id="team-x",
                uploaded_by="user-x",
                filename="invoice.pdf",
                mime_type="application/pdf",
                checksum="checksum-job-1",
                storage_uri=str(self.test_dir / "invoice.pdf"),
                page_count=1,
            )
            session.add(document)
            session.add(
                Job(
                    id=job_id,
                    document_id=document.id,
                    status=status,
                    attempt_count=1,
                    error_code=error_code,
                    error_message=error_message,
                    started_at=datetime(2026, 2, 15, 18, 0, 0, tzinfo=timezone.utc),
                    finished_at=datetime(2026, 2, 15, 18, 0, 5, tzinfo=timezone.utc),
                )
            )
            session.commit()
        finally:
            session.close()

    def test_get_job_status_returns_job_details(self) -> None:
        job_id = "job-status-1"
        self._insert_document_and_job(job_id=job_id, status="completed")

        response = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        data = payload["data"]
        self.assertEqual(data["job_id"], job_id)
        self.assertEqual(data["document_id"], "doc-job-1")
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["attempt_count"], 1)
        self.assertRegex(data["started_at"], TIMESTAMP_PATTERN)
        self.assertRegex(data["finished_at"], TIMESTAMP_PATTERN)
        self.assertRegex(data["created_at"], TIMESTAMP_PATTERN)
        self.assertIsNone(data["error"])

    def test_get_job_status_returns_error_payload_for_failed_job(self) -> None:
        job_id = "job-status-failed"
        self._insert_document_and_job(
            job_id=job_id,
            status="failed",
            error_code="PROCESSING_ERROR",
            error_message="model timeout",
        )

        response = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"]["code"], "PROCESSING_ERROR")
        self.assertEqual(data["error"]["message"], "model timeout")

    def test_get_job_status_returns_404_when_missing(self) -> None:
        response = self.client.get("/api/jobs/missing-job")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "JOB_NOT_FOUND")
        self.assertEqual(payload["error"]["details"]["job_id"], "missing-job")


if __name__ == "__main__":
    unittest.main()
