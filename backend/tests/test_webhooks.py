import os
import shutil
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from svandoc_backend.db import Base
from svandoc_backend.models.webhook_delivery_log import WebhookDeliveryLog
from svandoc_backend.webhooks import deliver_webhook_event


class WebhookDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"webhooks-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "webhooks-test.db"
        self.engine = sa.create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.SessionTesting = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.previous_webhook_endpoints = os.environ.get("WEBHOOK_ENDPOINTS")
        self.previous_signing_secret = os.environ.get("WEBHOOK_SIGNING_SECRET")
        self.previous_max_attempts = os.environ.get("WEBHOOK_MAX_ATTEMPTS")
        self.previous_timeout = os.environ.get("WEBHOOK_TIMEOUT_SECONDS")
        self.previous_backoff = os.environ.get("WEBHOOK_RETRY_BACKOFF_SECONDS")
        os.environ.pop("WEBHOOK_ENDPOINTS", None)
        os.environ.pop("WEBHOOK_SIGNING_SECRET", None)
        os.environ.pop("WEBHOOK_MAX_ATTEMPTS", None)
        os.environ.pop("WEBHOOK_TIMEOUT_SECONDS", None)
        os.environ.pop("WEBHOOK_RETRY_BACKOFF_SECONDS", None)

    def tearDown(self) -> None:
        if self.previous_webhook_endpoints is None:
            os.environ.pop("WEBHOOK_ENDPOINTS", None)
        else:
            os.environ["WEBHOOK_ENDPOINTS"] = self.previous_webhook_endpoints
        if self.previous_signing_secret is None:
            os.environ.pop("WEBHOOK_SIGNING_SECRET", None)
        else:
            os.environ["WEBHOOK_SIGNING_SECRET"] = self.previous_signing_secret
        if self.previous_max_attempts is None:
            os.environ.pop("WEBHOOK_MAX_ATTEMPTS", None)
        else:
            os.environ["WEBHOOK_MAX_ATTEMPTS"] = self.previous_max_attempts
        if self.previous_timeout is None:
            os.environ.pop("WEBHOOK_TIMEOUT_SECONDS", None)
        else:
            os.environ["WEBHOOK_TIMEOUT_SECONDS"] = self.previous_timeout
        if self.previous_backoff is None:
            os.environ.pop("WEBHOOK_RETRY_BACKOFF_SECONDS", None)
        else:
            os.environ["WEBHOOK_RETRY_BACKOFF_SECONDS"] = self.previous_backoff

        self.engine.dispose()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_delivery_is_noop_without_configuration(self) -> None:
        session = self.SessionTesting()
        try:
            delivered_count = deliver_webhook_event(
                session,
                event_type="job.completed",
                data={"job_id": "job-1", "document_id": "doc-1"},
            )
            self.assertEqual(delivered_count, 0)
            logs = session.query(WebhookDeliveryLog).all()
            self.assertEqual(logs, [])
        finally:
            session.close()

    def test_delivery_retries_and_persists_attempt_logs(self) -> None:
        os.environ["WEBHOOK_ENDPOINTS"] = "https://example.invalid/webhook"
        os.environ["WEBHOOK_SIGNING_SECRET"] = "test-secret"
        os.environ["WEBHOOK_MAX_ATTEMPTS"] = "3"
        os.environ["WEBHOOK_RETRY_BACKOFF_SECONDS"] = "0.001"

        with patch("httpx.Client.post") as mocked_post:
            mocked_post.side_effect = [
                SimpleNamespace(status_code=500),
                SimpleNamespace(status_code=200),
            ]
            session = self.SessionTesting()
            try:
                delivered_count = deliver_webhook_event(
                    session,
                    event_type="export.created",
                    data={"artifact_id": "art-1", "document_id": "doc-1"},
                )
            finally:
                session.close()

        self.assertEqual(delivered_count, 1)
        session = self.SessionTesting()
        try:
            logs = session.query(WebhookDeliveryLog).order_by(WebhookDeliveryLog.attempt_number.asc()).all()
        finally:
            session.close()
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].delivery_status, "failed")
        self.assertEqual(logs[0].response_status_code, 500)
        self.assertEqual(logs[1].delivery_status, "delivered")
        self.assertEqual(logs[1].response_status_code, 200)

    def test_delivery_sets_signature_headers(self) -> None:
        os.environ["WEBHOOK_ENDPOINTS"] = "https://example.invalid/webhook"
        os.environ["WEBHOOK_SIGNING_SECRET"] = "header-secret"
        os.environ["WEBHOOK_MAX_ATTEMPTS"] = "1"

        with patch("httpx.Client.post", return_value=SimpleNamespace(status_code=202)) as mocked_post:
            session = self.SessionTesting()
            try:
                delivered_count = deliver_webhook_event(
                    session,
                    event_type="job.failed",
                    data={"job_id": "job-2", "document_id": "doc-2", "error_code": "PROCESSING_ERROR"},
                )
            finally:
                session.close()

        self.assertEqual(delivered_count, 1)
        call_kwargs = mocked_post.call_args.kwargs
        headers = call_kwargs["headers"]
        self.assertEqual(headers["X-SvanDoc-Event"], "job.failed")
        self.assertTrue(headers["X-SvanDoc-Event-Id"])
        self.assertTrue(headers["X-SvanDoc-Signature"].startswith("sha256="))


if __name__ == "__main__":
    unittest.main()
