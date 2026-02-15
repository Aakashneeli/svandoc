import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base
from svandoc_backend.models.document import Document
from svandoc_backend.models.document_deletion_event import DocumentDeletionEvent
from svandoc_backend.models.job import Job
from svandoc_backend.retention import hard_delete_expired_documents


class RetentionCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / "retention-cleanup"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.storage_dir = self.test_dir / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.test_dir / "retention.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_retention_days = os.environ.get("DOCUMENT_RETENTION_DAYS")
        os.environ["DOCUMENT_RETENTION_DAYS"] = "30"

    def tearDown(self) -> None:
        self.engine.dispose()
        if self.previous_retention_days is None:
            os.environ.pop("DOCUMENT_RETENTION_DAYS", None)
        else:
            os.environ["DOCUMENT_RETENTION_DAYS"] = self.previous_retention_days
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _insert_document(self, document_id: str, *, created_at: datetime) -> Path:
        file_path = self.storage_dir / f"{document_id}.pdf"
        file_path.write_bytes(b"%PDF-1.7 retention")
        session = self.SessionTesting()
        try:
            session.add(
                Document(
                    id=document_id,
                    team_id="team-retention",
                    uploaded_by="uploader",
                    filename=f"{document_id}.pdf",
                    mime_type="application/pdf",
                    checksum=f"checksum-{document_id}",
                    storage_uri=str(file_path),
                    page_count=1,
                    created_at=created_at,
                )
            )
            session.add(
                Job(
                    id=f"job-{document_id}",
                    document_id=document_id,
                    status="queued",
                )
            )
            session.commit()
        finally:
            session.close()
        return file_path

    def test_hard_delete_expired_documents_removes_old_rows_and_writes_audit_event(self) -> None:
        now = datetime(2026, 2, 15, tzinfo=timezone.utc)
        old_file = self._insert_document("doc-old", created_at=now - timedelta(days=60))
        new_file = self._insert_document("doc-new", created_at=now - timedelta(days=5))

        session = self.SessionTesting()
        try:
            result = hard_delete_expired_documents(session, now=now, deleted_by="retention-bot")
        finally:
            session.close()

        self.assertEqual(result["deleted_document_count"], 1)
        self.assertEqual(result["deleted_storage_object_count"], 1)
        self.assertEqual(result["deleted_document_ids"], ["doc-old"])
        self.assertFalse(old_file.exists())
        self.assertTrue(new_file.exists())

        session = self.SessionTesting()
        try:
            old_doc = session.get(Document, "doc-old")
            new_doc = session.get(Document, "doc-new")
            old_job = session.get(Job, "job-doc-old")
            audit_rows = (
                session.query(DocumentDeletionEvent)
                .filter(DocumentDeletionEvent.document_id == "doc-old")
                .all()
            )
        finally:
            session.close()

        self.assertIsNone(old_doc)
        self.assertIsNotNone(new_doc)
        self.assertIsNone(old_job)
        self.assertEqual(len(audit_rows), 1)
        self.assertEqual(audit_rows[0].deleted_by, "retention-bot")
        self.assertEqual(audit_rows[0].delete_reason, "retention_policy")


if __name__ == "__main__":
    unittest.main()
