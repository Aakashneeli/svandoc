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
from svandoc_backend.models.job import Job


class RoleAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"authorization-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "authorization-test.db"
        self.storage_dir = self.test_dir / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        self.previous_storage_backend = os.environ.get("STORAGE_BACKEND")
        self.previous_local_storage = os.environ.get("LOCAL_STORAGE_PATH")
        os.environ["QUEUE_BACKEND"] = "disabled"
        os.environ["STORAGE_BACKEND"] = "local"
        os.environ["LOCAL_STORAGE_PATH"] = str(self.storage_dir)

        def override_db_session():
            session = self.SessionTesting()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_db_session
        self.client = TestClient(app)
        self._seed_document_bundle(document_id="doc-rbac-1", job_id="job-rbac-1")

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend
        if self.previous_storage_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = self.previous_storage_backend
        if self.previous_local_storage is None:
            os.environ.pop("LOCAL_STORAGE_PATH", None)
        else:
            os.environ["LOCAL_STORAGE_PATH"] = self.previous_local_storage
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_document_bundle(self, document_id: str, job_id: str) -> None:
        payload_path = self.storage_dir / "invoice.pdf"
        payload_path.write_bytes(b"%PDF-1.7 rbac")
        session = self.SessionTesting()
        try:
            session.add(
                Document(
                    id=document_id,
                    team_id="team-rbac",
                    uploaded_by="uploader",
                    filename="invoice.pdf",
                    mime_type="application/pdf",
                    checksum=f"checksum-{document_id}",
                    storage_uri=str(payload_path),
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
                    raw_ocr_text="RBAC RAW",
                    structured_payload={"vendor": {"name": "ACME"}, "amounts": {"total": 10.0}},
                    confidence_map={"overall": 0.9, "fields": {"amounts.total": 0.9}},
                    is_review_required=False,
                )
            )
            session.commit()
        finally:
            session.close()

    def test_viewer_cannot_upload(self) -> None:
        response = self.client.post(
            "/api/documents/upload",
            headers={"x-user-role": "viewer"},
            files=[("files", ("invoice.pdf", b"%PDF-1.7", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_editor_can_upload(self) -> None:
        response = self.client.post(
            "/api/documents/upload",
            headers={"x-user-role": "editor"},
            files=[("files", ("invoice-new.pdf", b"%PDF-1.7", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_viewer_can_read_job_and_extraction(self) -> None:
        job_response = self.client.get("/api/jobs/job-rbac-1", headers={"x-user-role": "viewer"})
        extraction_response = self.client.get(
            "/api/documents/doc-rbac-1/extraction",
            headers={"x-user-role": "viewer"},
        )
        self.assertEqual(job_response.status_code, 200)
        self.assertEqual(extraction_response.status_code, 200)

    def test_viewer_cannot_patch_extraction(self) -> None:
        response = self.client.patch(
            "/api/documents/doc-rbac-1/extraction",
            headers={"x-user-role": "viewer"},
            json={"corrections": [{"field_path": "vendor.name", "new_value": "ACME Corp"}]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_invalid_role_is_forbidden(self) -> None:
        response = self.client.get("/api/jobs/job-rbac-1", headers={"x-user-role": "owner"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
