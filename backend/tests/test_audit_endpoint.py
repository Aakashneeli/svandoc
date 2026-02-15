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
from svandoc_backend.models.user_correction import UserCorrection


class AuditEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"audit-endpoint-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "audit-endpoint-test.db"
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

    def _seed_document_audit(self, document_id: str) -> None:
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
            session.add(
                UserCorrection(
                    id=f"corr-{document_id}",
                    document_id=document_id,
                    field_path="amounts.total",
                    old_value=108.75,
                    new_value=109.99,
                    corrected_by="editor-a",
                )
            )
            session.add(
                ExportArtifact(
                    id=f"exp-{document_id}",
                    document_id=document_id,
                    format="csv",
                    storage_uri=str(self.test_dir / "artifact.csv"),
                    created_by="editor-a",
                )
            )
            session.commit()
        finally:
            session.close()

    def test_get_document_audit_returns_corrections_and_exports(self) -> None:
        document_id = "doc-audit-1"
        self._seed_document_audit(document_id)

        response = self.client.get(f"/api/documents/{document_id}/audit")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["document_id"], document_id)
        self.assertEqual(len(payload["corrections"]), 1)
        self.assertEqual(payload["corrections"][0]["field_path"], "amounts.total")
        self.assertEqual(payload["corrections"][0]["corrected_by"], "editor-a")
        self.assertEqual(len(payload["exports"]), 1)
        self.assertEqual(payload["exports"][0]["format"], "csv")
        self.assertEqual(payload["exports"][0]["created_by"], "editor-a")

    def test_get_document_audit_returns_not_found_for_missing_document(self) -> None:
        response = self.client.get("/api/documents/missing-document/audit")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "DOCUMENT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
