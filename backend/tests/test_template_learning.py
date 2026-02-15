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
from svandoc_backend.models.template_learning_rule import TemplateLearningRule


class TemplateLearningTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"template-learning-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "template-learning-test.db"
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
        self.headers = {"x-team-id": "team-learn", "x-user-id": "user-learn"}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_document_with_extraction(self, document_id: str) -> None:
        session = self.SessionTesting()
        try:
            session.add(
                Document(
                    id=document_id,
                    team_id="team-learn",
                    uploaded_by="user-learn",
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
                    doc_type="invoice",
                    raw_ocr_text="raw",
                    structured_payload={
                        "schema_version": "1.0.0",
                        "document_type": "invoice",
                        "metadata": {"document_id": document_id, "source_file_name": "invoice.pdf", "page_count": 1},
                        "vendor": {"name": "ACME", "tax_id": None, "address": None, "email": None},
                        "customer": None,
                        "invoice": {
                            "invoice_number": "INV-200",
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

    def test_repeated_opt_in_corrections_generate_learned_suggestion(self) -> None:
        self._insert_document_with_extraction("doc-learn-1")
        create_template = self.client.post(
            "/api/templates",
            headers=self.headers,
            json={
                "name": "Vendor Template",
                "doc_type": "invoice",
                "field_mapping": {"vendor_name": "vendor.name"},
                "schema_definition": {"fields": ["vendor_name"]},
            },
        )
        self.assertEqual(create_template.status_code, 200)
        template_id = create_template.json()["data"]["template_id"]

        apply_template = self.client.post(
            "/api/documents/doc-learn-1/templates/apply",
            headers=self.headers,
            json={"template_id": template_id},
        )
        self.assertEqual(apply_template.status_code, 200)

        for _ in range(2):
            correction = self.client.patch(
                "/api/documents/doc-learn-1/extraction",
                headers={**self.headers, "x-template-learning-opt-in": "true"},
                json={"corrections": [{"field_path": "vendor.name", "new_value": "ACME CORP"}]},
            )
            self.assertEqual(correction.status_code, 200)

        session = self.SessionTesting()
        try:
            rules = (
                session.query(TemplateLearningRule)
                .filter(TemplateLearningRule.template_id == template_id)
                .all()
            )
        finally:
            session.close()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].correction_count, 2)

        reapply = self.client.post(
            "/api/documents/doc-learn-1/templates/apply",
            headers=self.headers,
            json={"template_id": template_id},
        )
        self.assertEqual(reapply.status_code, 200)
        template_output = reapply.json()["data"]["structured_payload"]["template_output"]
        self.assertEqual(template_output["learned_suggestions"]["vendor_name"], "ACME CORP")

    def test_without_opt_in_learning_rules_are_not_recorded(self) -> None:
        self._insert_document_with_extraction("doc-learn-2")
        create_template = self.client.post(
            "/api/templates",
            headers=self.headers,
            json={
                "name": "Vendor Template",
                "doc_type": "invoice",
                "field_mapping": {"vendor_name": "vendor.name"},
            },
        )
        template_id = create_template.json()["data"]["template_id"]
        self.client.post(
            "/api/documents/doc-learn-2/templates/apply",
            headers=self.headers,
            json={"template_id": template_id},
        )
        correction = self.client.patch(
            "/api/documents/doc-learn-2/extraction",
            headers=self.headers,
            json={"corrections": [{"field_path": "vendor.name", "new_value": "ACME CORP"}]},
        )
        self.assertEqual(correction.status_code, 200)
        session = self.SessionTesting()
        try:
            count = session.query(TemplateLearningRule).count()
        finally:
            session.close()
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
