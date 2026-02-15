import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base, get_db_session
from svandoc_backend.main import app
from svandoc_backend.models.document import Document
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.user_correction import UserCorrection


class CorrectionEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"correction-endpoint-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "correction-endpoint-test.db"
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
                    structured_payload={
                        "vendor": {"name": "ACME Inc"},
                        "amounts": {"subtotal": 100.0, "tax": 8.75, "total": 108.75},
                        "line_items": [{"description": "Service Fee", "line_total": 108.75}],
                    },
                    confidence_map={"overall": 0.91, "fields": {"amounts.total": 0.96}},
                    is_review_required=False,
                )
            )
            session.commit()
        finally:
            session.close()

    def test_patch_document_extraction_updates_payload_and_persists_corrections(self) -> None:
        document_id = "doc-correct-1"
        self._insert_document(document_id)
        self._insert_extraction(document_id)

        response = self.client.patch(
            f"/api/documents/{document_id}/extraction",
            headers={"x-user-id": "editor-a"},
            json={
                "corrections": [
                    {"field_path": "amounts.total", "new_value": 109.99},
                    {"field_path": "line_items.0.description", "new_value": "Consulting Fee"},
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["correction_count"], 2)
        self.assertEqual(payload["data"]["corrected_by"], "editor-a")
        self.assertEqual(payload["data"]["structured_payload"]["amounts"]["total"], 109.99)
        self.assertEqual(payload["data"]["structured_payload"]["line_items"][0]["description"], "Consulting Fee")

        session = self.SessionTesting()
        try:
            extraction = (
                session.query(ExtractionResult).filter(ExtractionResult.document_id == document_id).one_or_none()
            )
            corrections = session.query(UserCorrection).filter(UserCorrection.document_id == document_id).all()
        finally:
            session.close()

        self.assertIsNotNone(extraction)
        assert extraction is not None
        self.assertEqual(extraction.structured_payload["amounts"]["total"], 109.99)
        self.assertEqual(len(corrections), 2)
        self.assertEqual(corrections[0].corrected_by, "editor-a")

    def test_patch_document_extraction_returns_404_when_document_missing(self) -> None:
        response = self.client.patch(
            "/api/documents/missing-document/extraction",
            json={"corrections": [{"field_path": "amounts.total", "new_value": 100.0}]},
        )
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "DOCUMENT_NOT_FOUND")

    def test_patch_document_extraction_returns_404_when_extraction_missing(self) -> None:
        document_id = "doc-correct-2"
        self._insert_document(document_id)

        response = self.client.patch(
            f"/api/documents/{document_id}/extraction",
            json={"corrections": [{"field_path": "amounts.total", "new_value": 100.0}]},
        )
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "EXTRACTION_NOT_FOUND")

    def test_patch_document_extraction_rejects_invalid_field_paths(self) -> None:
        document_id = "doc-correct-3"
        self._insert_document(document_id)
        self._insert_extraction(document_id)

        response = self.client.patch(
            f"/api/documents/{document_id}/extraction",
            json={"corrections": [{"field_path": "amounts.unknown_field", "new_value": 100.0}]},
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["invalid_field_paths"], ["amounts.unknown_field"])

        session = self.SessionTesting()
        try:
            correction_count = session.query(UserCorrection).filter(UserCorrection.document_id == document_id).count()
        finally:
            session.close()
        self.assertEqual(correction_count, 0)


if __name__ == "__main__":
    unittest.main()
