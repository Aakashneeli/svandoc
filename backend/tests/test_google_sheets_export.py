import unittest
from unittest.mock import Mock, patch

import httpx

from svandoc_backend.google_sheets_export import (
    GoogleSheetsExportError,
    append_to_google_sheet,
)


class GoogleSheetsExportTests(unittest.TestCase):
    def test_append_to_google_sheet_returns_update_metadata(self) -> None:
        response = Mock(spec=httpx.Response)
        response.json.return_value = {
            "updates": {
                "updatedRange": "InvoiceExports!A1:AA2",
                "updatedRows": 2,
            }
        }
        response.raise_for_status.return_value = None

        client = Mock()
        client.post.return_value = response
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=False)

        with patch("svandoc_backend.google_sheets_export.httpx.Client", return_value=context_manager):
            result = append_to_google_sheet(
                access_token="token-value",
                spreadsheet_id="sheet-id",
                sheet_name="InvoiceExports",
                headers=["document_id", "total"],
                row={"document_id": "doc-1", "total": "108.75"},
            )

        self.assertEqual(result.spreadsheet_id, "sheet-id")
        self.assertEqual(result.sheet_name, "InvoiceExports")
        self.assertEqual(result.updated_rows, 2)

    def test_append_to_google_sheet_raises_connector_error_on_http_failure(self) -> None:
        client = Mock()
        client.post.side_effect = httpx.HTTPStatusError(
            "bad request",
            request=httpx.Request("POST", "https://sheets.googleapis.com"),
            response=httpx.Response(400),
        )
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=client)
        context_manager.__exit__ = Mock(return_value=False)

        with patch("svandoc_backend.google_sheets_export.httpx.Client", return_value=context_manager):
            with self.assertRaises(GoogleSheetsExportError):
                append_to_google_sheet(
                    access_token="token-value",
                    spreadsheet_id="sheet-id",
                    sheet_name="InvoiceExports",
                    headers=["document_id"],
                    row={"document_id": "doc-1"},
                )


if __name__ == "__main__":
    unittest.main()

