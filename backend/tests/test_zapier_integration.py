import os
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
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job


class ZapierIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"zapier-integration-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "zapier-integration-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_zapier_key = os.environ.get("ZAPIER_API_KEY")
        os.environ["ZAPIER_API_KEY"] = "zapier-key-1"

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
        if self.previous_zapier_key is None:
            os.environ.pop("ZAPIER_API_KEY", None)
        else:
            os.environ["ZAPIER_API_KEY"] = self.previous_zapier_key
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_records(self) -> None:
        session = self.SessionTesting()
        try:
            finished_old = datetime(2026, 2, 15, 9, 0, tzinfo=timezone.utc)
            finished_new = datetime(2026, 2, 15, 11, 0, tzinfo=timezone.utc)
            session.add_all(
                [
                    Document(
                        id="doc-zapier-1",
                        team_id="team-a",
                        uploaded_by="user-a",
                        filename="invoice1.pdf",
                        mime_type="application/pdf",
                        checksum="checksum-zapier-1",
                        storage_uri="file:///tmp/invoice1.pdf",
                        page_count=1,
                    ),
                    Document(
                        id="doc-zapier-2",
                        team_id="team-a",
                        uploaded_by="user-a",
                        filename="invoice2.pdf",
                        mime_type="application/pdf",
                        checksum="checksum-zapier-2",
                        storage_uri="file:///tmp/invoice2.pdf",
                        page_count=1,
                    ),
                    Job(
                        id="job-zapier-old",
                        document_id="doc-zapier-1",
                        status="completed",
                        attempt_count=1,
                        finished_at=finished_old,
                    ),
                    Job(
                        id="job-zapier-new",
                        document_id="doc-zapier-2",
                        status="completed",
                        attempt_count=2,
                        finished_at=finished_new,
                    ),
                    ExtractionResult(
                        id="ext-zapier-2",
                        document_id="doc-zapier-2",
                        schema_version="1.0.0",
                        doc_type="invoice",
                        raw_ocr_text="raw",
                        structured_payload={
                            "schema_version": "1.0.0",
                            "document_type": "invoice",
                            "metadata": {"document_id": "doc-zapier-2", "source_file_name": "invoice2.pdf", "page_count": 1},
                            "vendor": {"name": "ACME", "tax_id": None, "address": None, "email": None},
                            "customer": {},
                            "invoice": {"invoice_number": "INV-2", "issue_date": "2026-02-15", "due_date": None, "purchase_order_number": None},
                            "amounts": {"currency": "USD", "subtotal": 10.0, "tax": 1.0, "shipping": None, "discount": None, "total": 11.0},
                            "line_items": [],
                            "payment_terms": None,
                            "confidence": {"overall": 0.9, "fields": {}},
                            "raw_text": "raw",
                            "review_required": False,
                            "warnings": [],
                        },
                        confidence_map={"overall": 0.9, "fields": {}},
                        is_review_required=False,
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()

    def test_trigger_requires_api_key(self) -> None:
        response = self.client.get("/api/integrations/zapier/triggers/job-completed")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_trigger_returns_completed_jobs_with_since_filter(self) -> None:
        self._seed_records()
        response = self.client.get(
            "/api/integrations/zapier/triggers/job-completed",
            headers={"x-zapier-api-key": "zapier-key-1"},
            params={"since": "2026-02-15T10:00:00Z"},
        )
        self.assertEqual(response.status_code, 200)
        jobs = response.json()["data"]["jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["job_id"], "job-zapier-new")
        self.assertEqual(jobs[0]["document_id"], "doc-zapier-2")

    def test_action_fetch_results_returns_extraction_payload(self) -> None:
        self._seed_records()
        response = self.client.get(
            "/api/integrations/zapier/actions/fetch-results",
            headers={"x-zapier-api-key": "zapier-key-1"},
            params={"document_id": "doc-zapier-2"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["document_id"], "doc-zapier-2")
        self.assertEqual(payload["doc_type"], "invoice")
        self.assertIn("structured_payload", payload)

    def test_action_fetch_results_returns_not_found(self) -> None:
        response = self.client.get(
            "/api/integrations/zapier/actions/fetch-results",
            headers={"x-zapier-api-key": "zapier-key-1"},
            params={"document_id": "missing-doc"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "DOCUMENT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
