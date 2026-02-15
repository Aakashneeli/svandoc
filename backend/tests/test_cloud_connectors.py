import unittest
from unittest.mock import Mock, patch

import httpx

from svandoc_backend.cloud_connectors import (
    CloudConnectorError,
    upload_to_dropbox,
    upload_to_google_drive,
    upload_to_onedrive,
)


class CloudConnectorsTests(unittest.TestCase):
    def _mock_client_context(self, response: Mock | None = None, side_effect: Exception | None = None) -> Mock:
        client = Mock()
        if side_effect is not None:
            client.post.side_effect = side_effect
            client.put.side_effect = side_effect
        else:
            assert response is not None
            client.post.return_value = response
            client.put.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=False)
        return context_manager

    def test_upload_to_google_drive_returns_storage_uri(self) -> None:
        response = Mock(spec=httpx.Response)
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "drive-file-1"}
        with patch(
            "svandoc_backend.cloud_connectors.httpx.Client",
            return_value=self._mock_client_context(response=response),
        ):
            result = upload_to_google_drive(
                access_token="token",
                filename="doc.json",
                content=b"{}",
                mime_type="application/json",
            )
        self.assertEqual(result.storage_uri, "gdrive://drive-file-1")

    def test_upload_to_onedrive_returns_storage_uri(self) -> None:
        response = Mock(spec=httpx.Response)
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "onedrive-file-1"}
        with patch(
            "svandoc_backend.cloud_connectors.httpx.Client",
            return_value=self._mock_client_context(response=response),
        ):
            result = upload_to_onedrive(
                access_token="token",
                filename="doc.json",
                content=b"{}",
            )
        self.assertEqual(result.storage_uri, "onedrive://onedrive-file-1")

    def test_upload_to_dropbox_returns_storage_uri(self) -> None:
        response = Mock(spec=httpx.Response)
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "dropbox-file-1"}
        with patch(
            "svandoc_backend.cloud_connectors.httpx.Client",
            return_value=self._mock_client_context(response=response),
        ):
            result = upload_to_dropbox(
                access_token="token",
                filename="doc.json",
                content=b"{}",
            )
        self.assertEqual(result.storage_uri, "dropbox://dropbox-file-1")

    def test_upload_raises_cloud_connector_error_on_http_failure(self) -> None:
        http_error = httpx.HTTPStatusError(
            "forbidden",
            request=httpx.Request("POST", "https://example.com"),
            response=httpx.Response(403),
        )
        with patch(
            "svandoc_backend.cloud_connectors.httpx.Client",
            return_value=self._mock_client_context(side_effect=http_error),
        ):
            with self.assertRaises(CloudConnectorError):
                upload_to_google_drive(
                    access_token="token",
                    filename="doc.json",
                    content=b"{}",
                    mime_type="application/json",
                )


if __name__ == "__main__":
    unittest.main()

