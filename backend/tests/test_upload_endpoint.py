import hashlib
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
from svandoc_backend.models.job import Job


class UploadEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"upload-endpoint-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.storage_dir = self.test_dir / "storage"
        self.db_path = self.test_dir / "upload-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_storage = os.environ.get("LOCAL_STORAGE_PATH")
        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        self.previous_storage_backend = os.environ.get("STORAGE_BACKEND")
        self.previous_s3_bucket = os.environ.get("S3_BUCKET")
        self.previous_s3_stub_storage_path = os.environ.get("S3_STUB_STORAGE_PATH")
        self.previous_max_upload_mb = os.environ.get("MAX_UPLOAD_MB")
        self.previous_max_upload_pages = os.environ.get("MAX_UPLOAD_PAGES")
        os.environ["LOCAL_STORAGE_PATH"] = str(self.storage_dir)
        os.environ["QUEUE_BACKEND"] = "disabled"
        os.environ["STORAGE_BACKEND"] = "local"
        os.environ["MAX_UPLOAD_MB"] = "25"
        os.environ["MAX_UPLOAD_PAGES"] = "20"

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
        if self.previous_queue_backend is None:
            os.environ.pop("QUEUE_BACKEND", None)
        else:
            os.environ["QUEUE_BACKEND"] = self.previous_queue_backend
        if self.previous_storage_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = self.previous_storage_backend
        if self.previous_s3_bucket is None:
            os.environ.pop("S3_BUCKET", None)
        else:
            os.environ["S3_BUCKET"] = self.previous_s3_bucket
        if self.previous_s3_stub_storage_path is None:
            os.environ.pop("S3_STUB_STORAGE_PATH", None)
        else:
            os.environ["S3_STUB_STORAGE_PATH"] = self.previous_s3_stub_storage_path
        if self.previous_max_upload_mb is None:
            os.environ.pop("MAX_UPLOAD_MB", None)
        else:
            os.environ["MAX_UPLOAD_MB"] = self.previous_max_upload_mb
        if self.previous_max_upload_pages is None:
            os.environ.pop("MAX_UPLOAD_PAGES", None)
        else:
            os.environ["MAX_UPLOAD_PAGES"] = self.previous_max_upload_pages
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_upload_persists_document_metadata_and_job(self) -> None:
        file_content = b"%PDF-1.7 test payload"
        response = self.client.post(
            "/api/documents/upload",
            headers={
                "x-team-id": "team_a",
                "x-user-id": "user_a",
            },
            data={"doc_type_hint": "invoice"},
            files=[("files", ("invoice.pdf", file_content, "application/pdf"))],
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        document_ids = payload["data"]["document_ids"]
        job_ids = payload["data"]["job_ids"]
        self.assertEqual(len(document_ids), 1)
        self.assertEqual(len(job_ids), 1)

        session = self.SessionTesting()
        try:
            document = session.get(Document, document_ids[0])
            job = session.get(Job, job_ids[0])
        finally:
            session.close()

        self.assertIsNotNone(document)
        self.assertIsNotNone(job)
        assert document is not None
        assert job is not None
        self.assertEqual(document.team_id, "team_a")
        self.assertEqual(document.uploaded_by, "user_a")
        self.assertEqual(document.filename, "invoice.pdf")
        self.assertEqual(document.mime_type, "application/pdf")
        self.assertEqual(document.page_count, 1)
        self.assertEqual(document.checksum, hashlib.sha256(file_content).hexdigest())
        self.assertEqual(job.document_id, document.id)
        self.assertEqual(job.status, "queued")

        stored_path = Path(document.storage_uri)
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_bytes(), file_content)

    def test_batch_upload_returns_parallel_document_and_job_ids(self) -> None:
        response = self.client.post(
            "/api/documents/upload",
            files=[
                ("files", ("one.pdf", b"%PDF-one", "application/pdf")),
                ("files", ("two.jpg", b"\xff\xd8\xff", "image/jpeg")),
            ],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        document_ids = payload["data"]["document_ids"]
        job_ids = payload["data"]["job_ids"]

        self.assertEqual(len(document_ids), 2)
        self.assertEqual(len(job_ids), 2)

        session = self.SessionTesting()
        try:
            document_count = session.query(Document).count()
            job_count = session.query(Job).count()
        finally:
            session.close()

        self.assertEqual(document_count, 2)
        self.assertEqual(job_count, 2)

    def test_upload_rejects_duplicate_against_existing_document(self) -> None:
        file_content = b"%PDF-1.7 same payload"
        first = self.client.post(
            "/api/documents/upload",
            files=[("files", ("first.pdf", file_content, "application/pdf"))],
        )
        self.assertEqual(first.status_code, 200)
        first_document_id = first.json()["data"]["document_ids"][0]

        second = self.client.post(
            "/api/documents/upload",
            files=[("files", ("second.pdf", file_content, "application/pdf"))],
        )
        self.assertEqual(second.status_code, 409)
        payload = second.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "DUPLICATE_DOCUMENT")
        duplicates = payload["error"]["details"]["duplicates"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["reason"], "already_exists")
        self.assertEqual(duplicates[0]["document_id"], first_document_id)

        session = self.SessionTesting()
        try:
            self.assertEqual(session.query(Document).count(), 1)
            self.assertEqual(session.query(Job).count(), 1)
        finally:
            session.close()

    def test_upload_rejects_duplicates_inside_same_request(self) -> None:
        duplicate_bytes = b"%PDF-1.7 duplicate in batch"
        response = self.client.post(
            "/api/documents/upload",
            files=[
                ("files", ("one.pdf", duplicate_bytes, "application/pdf")),
                ("files", ("two.pdf", duplicate_bytes, "application/pdf")),
            ],
        )
        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "DUPLICATE_DOCUMENT")
        duplicates = payload["error"]["details"]["duplicates"]
        self.assertEqual(len(duplicates), 2)
        reasons = {item["reason"] for item in duplicates}
        self.assertEqual(reasons, {"duplicate_in_request"})

        session = self.SessionTesting()
        try:
            self.assertEqual(session.query(Document).count(), 0)
            self.assertEqual(session.query(Job).count(), 0)
        finally:
            session.close()

    def test_upload_rejects_unsupported_file_types_with_structured_error(self) -> None:
        response = self.client.post(
            "/api/documents/upload",
            files=[("files", ("notes.txt", b"hello", "text/plain"))],
        )
        self.assertEqual(response.status_code, 400)

        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertIsNone(payload["data"])
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["retryable"], False)
        self.assertEqual(payload["error"]["details"]["files"][0]["filename"], "notes.txt")

        session = self.SessionTesting()
        try:
            self.assertEqual(session.query(Document).count(), 0)
            self.assertEqual(session.query(Job).count(), 0)
        finally:
            session.close()

    def test_upload_rejects_file_larger_than_configured_limit(self) -> None:
        os.environ["MAX_UPLOAD_MB"] = "1"
        payload = b"a" * ((1024 * 1024) + 1)

        response = self.client.post(
            "/api/documents/upload",
            files=[("files", ("big.pdf", payload, "application/pdf"))],
        )
        self.assertEqual(response.status_code, 400)
        details = response.json()["error"]["details"]["files"][0]
        self.assertIn("File size exceeds limit of 1 MB.", details["issues"])

    def test_upload_rejects_pdf_page_count_above_limit(self) -> None:
        os.environ["MAX_UPLOAD_PAGES"] = "1"
        fake_pdf_with_two_pages = b"%PDF-1.7\n/Type /Page\nsomething\n/Type /Page\n"

        response = self.client.post(
            "/api/documents/upload",
            files=[("files", ("many-pages.pdf", fake_pdf_with_two_pages, "application/pdf"))],
        )
        self.assertEqual(response.status_code, 400)
        details = response.json()["error"]["details"]["files"][0]
        self.assertIn("Page count exceeds limit of 1 pages.", details["issues"])

    def test_upload_supports_s3_storage_stub_mode(self) -> None:
        os.environ["STORAGE_BACKEND"] = "s3"
        os.environ["S3_BUCKET"] = "svandoc-test-bucket"
        s3_stub_root = self.test_dir / "s3-stub"
        os.environ["S3_STUB_STORAGE_PATH"] = str(s3_stub_root)
        file_content = b"%PDF-1.7 stub mode payload"

        response = self.client.post(
            "/api/documents/upload",
            files=[("files", ("invoice.pdf", file_content, "application/pdf"))],
        )
        self.assertEqual(response.status_code, 200)

        document_id = response.json()["data"]["document_ids"][0]
        session = self.SessionTesting()
        try:
            document = session.get(Document, document_id)
        finally:
            session.close()

        self.assertIsNotNone(document)
        assert document is not None
        self.assertTrue(document.storage_uri.startswith("s3://svandoc-test-bucket/"))
        expected_stub_file = s3_stub_root / "svandoc-test-bucket" / document_id / "invoice.pdf"
        self.assertTrue(expected_stub_file.exists())
        self.assertEqual(expected_stub_file.read_bytes(), file_content)

    def test_upload_returns_configuration_error_for_unknown_storage_backend(self) -> None:
        os.environ["STORAGE_BACKEND"] = "unknown-backend"
        response = self.client.post(
            "/api/documents/upload",
            files=[("files", ("invoice.pdf", b"%PDF-1.7", "application/pdf"))],
        )
        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "CONFIGURATION_ERROR")


if __name__ == "__main__":
    unittest.main()
