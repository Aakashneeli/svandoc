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


class ExtractionTemplateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"template-api-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "template-api-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        def override_db_session():
            session = self.SessionTesting()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_db_session
        self.client = TestClient(app)
        self.headers = {"x-team-id": "team-templates", "x-user-id": "user-templates"}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_document_with_extraction(self, document_id: str, doc_type: str = "invoice") -> None:
        session = self.SessionTesting()
        try:
            session.add(
                Document(
                    id=document_id,
                    team_id="team-templates",
                    uploaded_by="user-templates",
                    filename="invoice.pdf",
                    mime_type="application/pdf",
                    checksum=f"checksum-{document_id}",
                    storage_uri=str(self.test_dir / "invoice.pdf"),
                    page_count=1,
                )
            )
            session.add(
                ExtractionResult(
                    id=f"ext-{document_id}",
                    document_id=document_id,
                    schema_version="1.0.0",
                    doc_type=doc_type,
                    raw_ocr_text="raw",
                    structured_payload={
                        "schema_version": "1.0.0",
                        "document_type": "invoice",
                        "metadata": {"document_id": document_id, "source_file_name": "invoice.pdf", "page_count": 1},
                        "vendor": {"name": "ACME", "tax_id": None, "address": None, "email": None},
                        "customer": None,
                        "invoice": {
                            "invoice_number": "INV-100",
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
                        "raw_text": "raw",
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

    def test_create_and_list_templates(self) -> None:
        create_response = self.client.post(
            "/api/templates",
            headers=self.headers,
            json={
                "name": "Invoice Template A",
                "doc_type": "invoice",
                "schema_definition": {"fields": ["vendor_name", "invoice_ref"]},
                "field_mapping": {
                    "vendor_name": "vendor.name",
                    "invoice_ref": "invoice.invoice_number",
                },
            },
        )
        self.assertEqual(create_response.status_code, 200)
        template_id = create_response.json()["data"]["template_id"]
        self.assertTrue(template_id)

        list_response = self.client.get("/api/templates", headers=self.headers)
        self.assertEqual(list_response.status_code, 200)
        templates = list_response.json()["data"]["templates"]
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["name"], "Invoice Template A")

    def test_apply_template_to_extraction_persists_template_output(self) -> None:
        self._insert_document_with_extraction("doc-template-1")
        create_response = self.client.post(
            "/api/templates",
            headers=self.headers,
            json={
                "name": "Invoice Mapping",
                "doc_type": "invoice",
                "schema_definition": {"fields": ["vendor_name", "invoice_ref", "missing_field"]},
                "field_mapping": {
                    "vendor_name": "vendor.name",
                    "invoice_ref": "invoice.invoice_number",
                    "missing_field": "invoice.not_present",
                },
            },
        )
        template_id = create_response.json()["data"]["template_id"]

        apply_response = self.client.post(
            "/api/documents/doc-template-1/templates/apply",
            headers=self.headers,
            json={"template_id": template_id},
        )
        self.assertEqual(apply_response.status_code, 200)
        payload = apply_response.json()["data"]["structured_payload"]
        template_output = payload.get("template_output")
        self.assertIsInstance(template_output, dict)
        assert isinstance(template_output, dict)
        self.assertEqual(template_output["mapped_fields"]["vendor_name"], "ACME")
        self.assertIn("invoice.not_present", template_output["missing_paths"])

    def test_apply_template_rejects_doc_type_mismatch(self) -> None:
        self._insert_document_with_extraction("doc-template-2", doc_type="receipt")
        create_response = self.client.post(
            "/api/templates",
            headers=self.headers,
            json={
                "name": "Invoice Mapping",
                "doc_type": "invoice",
                "field_mapping": {"invoice_ref": "invoice.invoice_number"},
            },
        )
        template_id = create_response.json()["data"]["template_id"]

        apply_response = self.client.post(
            "/api/documents/doc-template-2/templates/apply",
            headers=self.headers,
            json={"template_id": template_id},
        )
        self.assertEqual(apply_response.status_code, 400)
        self.assertEqual(apply_response.json()["error"]["code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
