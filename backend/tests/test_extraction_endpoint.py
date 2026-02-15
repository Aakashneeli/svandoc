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
from svandoc_backend.models.extraction_result import ExtractionResult


TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class ExtractionEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"extraction-endpoint-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "extraction-endpoint-test.db"
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

    def _insert_document(self, document_id: str) -> None:
        session = self.SessionTesting()
        try:
            session.add(
                Document(
                    id=document_id,
                    team_id="team-a",
                    uploaded_by="user-a",
                    filename="invoice.pdf",
                    mime_type="application/pdf",
                    checksum=f"checksum-{document_id}",
                    storage_uri=str(self.test_dir / "invoice.pdf"),
                    page_count=1,
                )
            )
            session.commit()
        finally:
            session.close()

    def _insert_extraction(self, document_id: str) -> None:
        session = self.SessionTesting()
        try:
            session.add(
                ExtractionResult(
                    id=f"ext-{document_id}",
                    document_id=document_id,
                    schema_version="1.0.0",
                    doc_type="invoice",
                    raw_ocr_text="INVOICE RAW OCR",
                    structured_payload={"document_type": "invoice", "amounts": {"total": 108.75}},
                    confidence_map={"overall": 0.91, "fields": {"amounts.total": 0.96}},
                    is_review_required=False,
                    created_at=datetime(2026, 2, 15, 19, 15, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 2, 15, 19, 15, 2, tzinfo=timezone.utc),
                )
            )
            session.commit()
        finally:
            session.close()

    def test_get_document_extraction_returns_payload_and_confidence(self) -> None:
        document_id = "doc-ext-1"
        self._insert_document(document_id)
        self._insert_extraction(document_id)

        response = self.client.get(f"/api/documents/{document_id}/extraction")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")

        data = payload["data"]
        self.assertEqual(data["document_id"], document_id)
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertEqual(data["doc_type"], "invoice")
        self.assertEqual(data["review_required"], False)
        self.assertEqual(data["raw_ocr_text"], "INVOICE RAW OCR")
        self.assertEqual(data["structured_payload"]["document_type"], "invoice")
        self.assertEqual(data["confidence_map"]["overall"], 0.91)
        self.assertRegex(data["created_at"], TIMESTAMP_PATTERN)
        self.assertRegex(data["updated_at"], TIMESTAMP_PATTERN)

    def test_get_document_extraction_returns_404_when_document_missing(self) -> None:
        response = self.client.get("/api/documents/missing-doc/extraction")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "DOCUMENT_NOT_FOUND")
        self.assertEqual(payload["error"]["details"]["document_id"], "missing-doc")

    def test_get_document_extraction_returns_404_when_extraction_missing(self) -> None:
        document_id = "doc-without-extraction"
        self._insert_document(document_id)

        response = self.client.get(f"/api/documents/{document_id}/extraction")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "EXTRACTION_NOT_FOUND")
        self.assertEqual(payload["error"]["details"]["document_id"], document_id)


if __name__ == "__main__":
    unittest.main()
