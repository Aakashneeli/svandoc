import os
import shutil
import unittest
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base, get_db_session
from svandoc_backend.main import app
from svandoc_backend.models.document import Document
from svandoc_backend.models.job import Job


class EmailIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"email-intake-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.storage_dir = self.test_dir / "storage"
        self.db_path = self.test_dir / "email-intake-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_storage = os.environ.get("LOCAL_STORAGE_PATH")
        self.previous_queue_backend = os.environ.get("QUEUE_BACKEND")
        self.previous_storage_backend = os.environ.get("STORAGE_BACKEND")
        self.previous_ingestion_domain = os.environ.get("EMAIL_INGESTION_DOMAIN")
        self.previous_allowed_domains = os.environ.get("EMAIL_ALLOWED_SENDER_DOMAINS")
        self.previous_max_attachments = os.environ.get("EMAIL_MAX_ATTACHMENTS")
        os.environ["LOCAL_STORAGE_PATH"] = str(self.storage_dir)
        os.environ["QUEUE_BACKEND"] = "disabled"
        os.environ["STORAGE_BACKEND"] = "local"
        os.environ["EMAIL_INGESTION_DOMAIN"] = "mail.svandoc.test"
        os.environ["EMAIL_ALLOWED_SENDER_DOMAINS"] = "trusted.test"
        os.environ["EMAIL_MAX_ATTACHMENTS"] = "2"

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
        if self.previous_ingestion_domain is None:
            os.environ.pop("EMAIL_INGESTION_DOMAIN", None)
        else:
            os.environ["EMAIL_INGESTION_DOMAIN"] = self.previous_ingestion_domain
        if self.previous_allowed_domains is None:
            os.environ.pop("EMAIL_ALLOWED_SENDER_DOMAINS", None)
        else:
            os.environ["EMAIL_ALLOWED_SENDER_DOMAINS"] = self.previous_allowed_domains
        if self.previous_max_attachments is None:
            os.environ.pop("EMAIL_MAX_ATTACHMENTS", None)
        else:
            os.environ["EMAIL_MAX_ATTACHMENTS"] = self.previous_max_attachments
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _build_message(self, *, to_address: str, from_address: str, attachment_count: int = 1) -> bytes:
        message = EmailMessage()
        message["From"] = from_address
        message["To"] = to_address
        message["Subject"] = "Forwarded invoices"
        message.set_content("Attached documents.")
        for index in range(attachment_count):
            message.add_attachment(
                b"%PDF-1.7 email payload",
                maintype="application",
                subtype="pdf",
                filename=f"invoice-{index + 1}.pdf",
            )
        return message.as_bytes()

    def test_email_intake_persists_documents_and_jobs(self) -> None:
        message_bytes = self._build_message(
            to_address="team_a@mail.svandoc.test",
            from_address="sender@trusted.test",
        )
        response = self.client.post(
            "/api/documents/email-intake",
            headers={"x-team-id": "team_a", "x-user-id": "user_a"},
            files=[("message", ("forwarded.eml", message_bytes, "message/rfc822"))],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["to_address"], "team_a@mail.svandoc.test")
        self.assertEqual(len(payload["document_ids"]), 1)
        self.assertEqual(len(payload["job_ids"]), 1)

        session = self.SessionTesting()
        try:
            document = session.get(Document, payload["document_ids"][0])
            job = session.get(Job, payload["job_ids"][0])
        finally:
            session.close()
        self.assertIsNotNone(document)
        self.assertIsNotNone(job)
        assert document is not None
        assert job is not None
        self.assertEqual(document.team_id, "team_a")
        self.assertEqual(job.status, "queued")

    def test_email_intake_rejects_wrong_workspace_address(self) -> None:
        message_bytes = self._build_message(
            to_address="other-team@mail.svandoc.test",
            from_address="sender@trusted.test",
        )
        response = self.client.post(
            "/api/documents/email-intake",
            headers={"x-team-id": "team_a"},
            files=[("message", ("forwarded.eml", message_bytes, "message/rfc822"))],
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["expected_to_address"], "team_a@mail.svandoc.test")

    def test_email_intake_rejects_untrusted_sender_domain(self) -> None:
        message_bytes = self._build_message(
            to_address="team_a@mail.svandoc.test",
            from_address="sender@untrusted.test",
        )
        response = self.client.post(
            "/api/documents/email-intake",
            headers={"x-team-id": "team_a"},
            files=[("message", ("forwarded.eml", message_bytes, "message/rfc822"))],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_email_intake_rejects_attachment_count_above_limit(self) -> None:
        message_bytes = self._build_message(
            to_address="team_a@mail.svandoc.test",
            from_address="sender@trusted.test",
            attachment_count=3,
        )
        response = self.client.post(
            "/api/documents/email-intake",
            headers={"x-team-id": "team_a"},
            files=[("message", ("forwarded.eml", message_bytes, "message/rfc822"))],
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["max_attachments"], 2)


if __name__ == "__main__":
    unittest.main()
