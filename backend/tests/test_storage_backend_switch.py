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


class StorageBackendSwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"storage-switch-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.local_storage_dir = self.test_dir / "local-storage"
        self.s3_stub_dir = self.test_dir / "s3-stub"
        self.db_path = self.test_dir / "storage-switch-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_env = {
            "QUEUE_BACKEND": os.environ.get("QUEUE_BACKEND"),
            "STORAGE_BACKEND": os.environ.get("STORAGE_BACKEND"),
            "LOCAL_STORAGE_PATH": os.environ.get("LOCAL_STORAGE_PATH"),
            "S3_BUCKET": os.environ.get("S3_BUCKET"),
            "S3_STUB_STORAGE_PATH": os.environ.get("S3_STUB_STORAGE_PATH"),
        }
        os.environ["QUEUE_BACKEND"] = "disabled"
        os.environ["LOCAL_STORAGE_PATH"] = str(self.local_storage_dir)
        os.environ["S3_BUCKET"] = "svandoc-switch-test"
        os.environ["S3_STUB_STORAGE_PATH"] = str(self.s3_stub_dir)

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
        for key, value in self.previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_extraction(self, document_id: str) -> None:
        session = self.SessionTesting()
        try:
            session.add(
                ExtractionResult(
                    id=f"ext-{document_id}",
                    document_id=document_id,
                    schema_version="1.0.0",
                    doc_type="invoice",
                    raw_ocr_text="INVOICE OCR RAW",
                    structured_payload={
                        "schema_version": "1.0.0",
                        "document_type": "invoice",
                        "metadata": {"document_id": document_id, "source_file_name": "invoice.pdf", "page_count": 1},
                        "vendor": {"name": "ACME Inc", "tax_id": None, "address": None, "email": None},
                        "customer": None,
                        "invoice": {
                            "invoice_number": "INV-1",
                            "issue_date": "2026-02-15",
                            "due_date": None,
                            "purchase_order_number": None,
                        },
                        "amounts": {
                            "currency": "USD",
                            "subtotal": 100.0,
                            "tax": 8.75,
                            "shipping": None,
                            "discount": None,
                            "total": 108.75,
                        },
                        "line_items": [
                            {"description": "Service Fee", "quantity": 1, "unit_price": 108.75, "line_total": 108.75}
                        ],
                        "payment_terms": None,
                        "confidence": {"overall": 0.95, "fields": {"amounts.total": 0.97}},
                        "raw_text": "INVOICE OCR RAW",
                        "review_required": False,
                        "warnings": [],
                    },
                    confidence_map={"overall": 0.95, "fields": {"amounts.total": 0.97}},
                    is_review_required=False,
                )
            )
            session.commit()
        finally:
            session.close()

    def _assert_document_stored_for_backend(self, backend: str, document_id: str) -> None:
        session = self.SessionTesting()
        try:
            document = session.get(Document, document_id)
        finally:
            session.close()
        self.assertIsNotNone(document)
        assert document is not None

        if backend == "local":
            stored_path = Path(document.storage_uri)
            self.assertTrue(stored_path.exists())
            self.assertIn(self.local_storage_dir.resolve(), stored_path.resolve().parents)
        else:
            self.assertTrue(document.storage_uri.startswith("s3://svandoc-switch-test/"))
            expected = self.s3_stub_dir / "svandoc-switch-test" / document_id / "invoice.pdf"
            self.assertTrue(expected.exists())

    def _assert_export_stored_for_backend(self, backend: str, artifact_id: str, document_id: str, storage_uri: str) -> None:
        if backend == "local":
            stored_path = Path(storage_uri)
            self.assertTrue(stored_path.exists())
            self.assertIn(self.local_storage_dir.resolve(), stored_path.resolve().parents)
            return

        self.assertTrue(storage_uri.startswith("s3://svandoc-switch-test/"))
        expected = self.s3_stub_dir / "svandoc-switch-test" / artifact_id / f"{document_id}.json"
        self.assertTrue(expected.exists())

    def test_upload_and_export_flow_passes_for_local_and_s3_backends(self) -> None:
        for backend in ("local", "s3"):
            with self.subTest(storage_backend=backend):
                os.environ["STORAGE_BACKEND"] = backend

                upload_response = self.client.post(
                    "/api/documents/upload",
                    files=[
                        (
                            "files",
                            (
                                "invoice.pdf",
                                f"%PDF-1.7 storage switch {backend}".encode("utf-8"),
                                "application/pdf",
                            ),
                        )
                    ],
                )
                self.assertEqual(upload_response.status_code, 200)
                document_id = upload_response.json()["data"]["document_ids"][0]
                self._assert_document_stored_for_backend(backend, document_id)

                self._insert_extraction(document_id)
                export_response = self.client.post(
                    f"/api/documents/{document_id}/export",
                    json={"format": "json"},
                )
                self.assertEqual(export_response.status_code, 200)
                export_data = export_response.json()["data"]
                self._assert_export_stored_for_backend(
                    backend,
                    export_data["artifact_id"],
                    document_id,
                    export_data["storage_uri"],
                )


if __name__ == "__main__":
    unittest.main()
