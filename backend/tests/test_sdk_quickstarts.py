import json
import os
import subprocess
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _MockSvanDocHandler(BaseHTTPRequestHandler):
    def _write_json(self, status_code: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _check_api_key(self) -> bool:
        return self.headers.get("x-api-key", "").strip() == "test-public-key"

    def _drain_request_body(self) -> None:
        length_raw = self.headers.get("Content-Length", "").strip()
        if not length_raw:
            return
        try:
            length = int(length_raw)
        except ValueError:
            return
        if length > 0:
            _ = self.rfile.read(length)

    def do_GET(self) -> None:  # noqa: N802
        if not self._check_api_key():
            self._write_json(401, {"status": "error", "data": None, "error": {"code": "UNAUTHORIZED"}})
            return
        if self.path == "/api/public/jobs/job-quickstart":
            self._write_json(
                200,
                {"status": "success", "data": {"job_id": "job-quickstart", "status": "completed"}, "error": None},
            )
            return
        if self.path == "/api/public/documents/doc-quickstart/extraction":
            self._write_json(
                200,
                {
                    "status": "success",
                    "data": {"document_id": "doc-quickstart", "doc_type": "invoice"},
                    "error": None,
                },
            )
            return
        self._write_json(404, {"status": "error", "data": None, "error": {"code": "NOT_FOUND"}})

    def do_POST(self) -> None:  # noqa: N802
        self._drain_request_body()
        if not self._check_api_key():
            self._write_json(401, {"status": "error", "data": None, "error": {"code": "UNAUTHORIZED"}})
            return
        if self.path == "/api/public/documents/upload":
            self._write_json(
                200,
                {
                    "status": "success",
                    "data": {"document_ids": ["doc-quickstart"], "job_ids": ["job-quickstart"]},
                    "error": None,
                },
            )
            return
        if self.path == "/api/public/documents/doc-quickstart/export":
            self._write_json(
                200,
                {
                    "status": "success",
                    "data": {
                        "artifact_id": "artifact-quickstart",
                        "document_id": "doc-quickstart",
                        "format": "json",
                        "storage_uri": "https://example.test/artifact.json",
                    },
                    "error": None,
                },
            )
            return
        self._write_json(404, {"status": "error", "data": None, "error": {"code": "NOT_FOUND"}})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        _ = format
        _ = args


class SdkQuickstartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _MockSvanDocHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_python_quickstart_runs_against_mock_api(self) -> None:
        env = os.environ.copy()
        env["SVANDOC_API_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        env["SVANDOC_API_KEY"] = "test-public-key"
        env["PYTHONPATH"] = "sdk/python"
        process = subprocess.run(
            ["myvenv\\Scripts\\python.exe", "sdk/python/examples/quickstart.py"],
            cwd=Path.cwd(),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, msg=process.stderr or process.stdout)
        self.assertIn("job.status completed", process.stdout)

    def test_typescript_quickstart_runs_against_mock_api(self) -> None:
        env = os.environ.copy()
        env["SVANDOC_API_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        env["SVANDOC_API_KEY"] = "test-public-key"
        process = subprocess.run(
            ["node", "sdk/typescript/examples/quickstart.mjs"],
            cwd=Path.cwd(),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, msg=process.stderr or process.stdout)
        self.assertIn("job.status completed", process.stdout)


if __name__ == "__main__":
    unittest.main()
