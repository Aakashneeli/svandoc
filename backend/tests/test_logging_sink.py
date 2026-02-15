import json
import logging
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from svandoc_backend.logging_sink import configure_structured_logging
from svandoc_backend.worker_logging import emit_worker_log


class StructuredLoggingSinkTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / "logging-sink-config"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.log_path = self.test_dir / "structured.log"
        self.previous_sink = os.environ.get("STRUCTURED_LOG_SINK_PATH")

    def tearDown(self) -> None:
        if self.previous_sink is None:
            os.environ.pop("STRUCTURED_LOG_SINK_PATH", None)
        else:
            os.environ["STRUCTURED_LOG_SINK_PATH"] = self.previous_sink
        configure_structured_logging(force=True)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_configure_structured_logging_uses_file_handler_when_sink_path_set(self) -> None:
        os.environ["STRUCTURED_LOG_SINK_PATH"] = str(self.log_path)
        configure_structured_logging(force=True)

        api_logger = logging.getLogger("svandoc.api")
        worker_logger = logging.getLogger("svandoc.worker")
        self.assertEqual(len(api_logger.handlers), 1)
        self.assertEqual(len(worker_logger.handlers), 1)
        self.assertIsInstance(api_logger.handlers[0], logging.FileHandler)
        self.assertIsInstance(worker_logger.handlers[0], logging.FileHandler)
        self.assertIn(str(self.log_path), str(getattr(api_logger.handlers[0], "baseFilename", "")))

    def test_worker_log_payload_contains_request_job_and_document_ids(self) -> None:
        with patch("svandoc_backend.worker_logging.worker_logger.info") as info_mock:
            emit_worker_log(
                event="worker_test",
                request_id="req-123",
                job_id="job-123",
                document_id="doc-123",
                status="processing",
                details={"retry": False},
            )

        info_mock.assert_called_once()
        serialized_payload = info_mock.call_args.args[0]
        payload = json.loads(serialized_payload)
        self.assertEqual(payload["event"], "worker_test")
        self.assertEqual(payload["request_id"], "req-123")
        self.assertEqual(payload["job_id"], "job-123")
        self.assertEqual(payload["document_id"], "doc-123")
        self.assertEqual(payload["status"], "processing")


if __name__ == "__main__":
    unittest.main()
