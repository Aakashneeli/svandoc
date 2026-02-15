import json
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
from svandoc_backend.models.export_artifact import ExportArtifact
from svandoc_backend.models.extraction_result import ExtractionResult
from svandoc_backend.models.job import Job


class PublicApiTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"public-api-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.storage_dir = self.test_dir / "storage"
        self.db_path = self.test_dir / "public-api-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_storage = os.environ.get("LOCAL_STORAGE_PATH")
        self.previous_storage_backend = os.environ.get("STORAGE_BACKEND")
        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        self.previous_public_keys = os.environ.get("PUBLIC_API_KEYS_JSON")
        os.environ["LOCAL_STORAGE_PATH"] = str(self.storage_dir)
        os.environ["STORAGE_BACKEND"] = "local"
        os.environ["QUEUE_BACKEND"] = "disabled"
        os.environ["PUBLIC_API_KEYS_JSON"] = json.dumps(
            [
                {
                    "id": "client-all",
                    "key": "public-key-all",
                    "scopes": ["documents:write", "jobs:read", "extractions:read", "exports:write"],
                },
                {
                    "id": "client-jobs",
                    "key": "public-key-jobs",
                    "scopes": ["jobs:read"],
                },
            ]
        )

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
        if self.previous_storage is None:
            os.environ.pop("LOCAL_STORAGE_PATH", None)
        else:
            os.environ["LOCAL_STORAGE_PATH"] = self.previous_storage
        if self.previous_storage_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = self.previous_storage_backend
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend
        if self.previous_public_keys is None:
            os.environ.pop("PUBLIC_API_KEYS_JSON", None)
        else:
            os.environ["PUBLIC_API_KEYS_JSON"] = self.previous_public_keys
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_document_fixture(self, document_id: str, job_id: str) -> None:
        session = self.SessionTesting()
        try:
            session.add(
                Document(
                    id=document_id,
                    team_id="team-public",
                    uploaded_by="user-public",
                    filename="invoice.pdf",
                    mime_type="application/pdf",
                    checksum=f"checksum-{document_id}",
                    storage_uri=str(self.test_dir / "invoice.pdf"),
                    page_count=1,
                )
            )
            session.add(
                Job(
                    id=job_id,
                    document_id=document_id,
                    status="completed",
                    attempt_count=1,
                )
            )
            session.add(
                ExtractionResult(
                    id=f"ext-{document_id}",
                    document_id=document_id,
                    schema_version="1.0.0",
                    doc_type="invoice",
                    raw_ocr_text="OCR",
                    structured_payload={
                        "schema_version": "1.0.0",
                        "document_type": "invoice",
                        "metadata": {"document_id": document_id, "source_file_name": "invoice.pdf", "page_count": 1},
                        "vendor": {"name": "ACME", "tax_id": None, "address": None, "email": None},
                        "customer": None,
                        "invoice": {
                            "invoice_number": "INV-PUBLIC-1",
                            "issue_date": "2026-02-16",
                            "due_date": None,
                            "purchase_order_number": None,
                        },
                        "amounts": {
                            "currency": "USD",
                            "subtotal": 10,
                            "tax": 1,
                            "shipping": None,
                            "discount": None,
                            "total": 11,
                        },
                        "line_items": [],
                        "payment_terms": None,
                        "confidence": {"overall": 0.9, "fields": {}},
                        "raw_text": "OCR",
                        "review_required": False,
                        "warnings": [],
                    },
                    confidence_map={"overall": 0.9, "fields": {}},
                    is_review_required=False,
                )
            )
            session.commit()
        finally:
            session.close()

    def test_public_api_requires_api_key(self) -> None:
        response = self.client.get("/api/public/jobs/job-1")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_public_api_rejects_missing_scope(self) -> None:
        self._insert_document_fixture("doc-public-scope", "job-public-scope")
        response = self.client.get(
            "/api/public/documents/doc-public-scope/extraction",
            headers={"x-api-key": "public-key-jobs"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_public_upload_allows_document_creation(self) -> None:
        response = self.client.post(
            "/api/public/documents/upload",
            headers={"x-api-key": "public-key-all"},
            files=[("files", ("invoice.pdf", b"%PDF-1.7 public", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(len(payload["document_ids"]), 1)
        self.assertEqual(len(payload["job_ids"]), 1)

    def test_public_job_extraction_and_export_flow(self) -> None:
        document_id = "doc-public-1"
        job_id = "job-public-1"
        self._insert_document_fixture(document_id, job_id)

        job_response = self.client.get(
            f"/api/public/jobs/{job_id}",
            headers={"x-api-key": "public-key-all"},
        )
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(job_response.json()["data"]["job_id"], job_id)

        extraction_response = self.client.get(
            f"/api/public/documents/{document_id}/extraction",
            headers={"x-api-key": "public-key-all"},
        )
        self.assertEqual(extraction_response.status_code, 200)
        self.assertEqual(extraction_response.json()["data"]["document_id"], document_id)

        export_response = self.client.post(
            f"/api/public/documents/{document_id}/export",
            headers={"x-api-key": "public-key-all"},
            json={"format": "json"},
        )
        self.assertEqual(export_response.status_code, 200)
        artifact_id = export_response.json()["data"]["artifact_id"]

        session = self.SessionTesting()
        try:
            artifact = session.get(ExportArtifact, artifact_id)
        finally:
            session.close()
        self.assertIsNotNone(artifact)
        assert artifact is not None
        self.assertEqual(artifact.document_id, document_id)


if __name__ == "__main__":
    unittest.main()
