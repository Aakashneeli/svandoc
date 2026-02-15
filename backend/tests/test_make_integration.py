import os
import unittest

from fastapi.testclient import TestClient

from svandoc_backend.main import app


class MakeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.previous_make_key = os.environ.get("MAKE_API_KEY")
        self.previous_make_api_base_url = os.environ.get("MAKE_API_BASE_URL")
        os.environ["MAKE_API_KEY"] = "make-key-1"
        os.environ["MAKE_API_BASE_URL"] = "https://api.svandoc.local"

    def tearDown(self) -> None:
        if self.previous_make_key is None:
            os.environ.pop("MAKE_API_KEY", None)
        else:
            os.environ["MAKE_API_KEY"] = self.previous_make_key
        if self.previous_make_api_base_url is None:
            os.environ.pop("MAKE_API_BASE_URL", None)
        else:
            os.environ["MAKE_API_BASE_URL"] = self.previous_make_api_base_url

    def test_make_templates_require_api_key(self) -> None:
        response = self.client.get("/api/integrations/make/templates")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_make_templates_return_upload_and_export_workflows(self) -> None:
        response = self.client.get(
            "/api/integrations/make/templates",
            headers={"x-make-api-key": "make-key-1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        templates = payload["templates"]
        self.assertEqual(len(templates), 2)

        upload_template = next(item for item in templates if item["id"] == "upload_to_status_polling")
        export_template = next(item for item in templates if item["id"] == "completed_job_to_export")

        self.assertIn("/api/documents/upload", upload_template["modules"][0]["url"])
        self.assertIn("/api/jobs/{{job_id}}", upload_template["modules"][2]["url"])
        self.assertEqual(export_template["modules"][0]["event_type"], "job.completed")
        self.assertIn("/api/documents/{{document_id}}/export", export_template["modules"][2]["url"])
        self.assertTrue(
            upload_template["modules"][0]["url"].startswith("https://api.svandoc.local")
        )


if __name__ == "__main__":
    unittest.main()
