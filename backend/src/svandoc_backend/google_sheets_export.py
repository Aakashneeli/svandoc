"""Google Sheets export connector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class GoogleSheetsExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleSheetsExportResult:
    spreadsheet_id: str
    sheet_name: str
    updated_range: str | None
    updated_rows: int | None


def append_to_google_sheet(
    *,
    access_token: str,
    spreadsheet_id: str,
    sheet_name: str,
    headers: list[str],
    row: dict[str, str],
    timeout_seconds: float = 10.0,
) -> GoogleSheetsExportResult:
    safe_sheet = sheet_name.strip() or "Sheet1"
    values = [headers, [row.get(header, "") for header in headers]]
    encoded_range = quote(f"{safe_sheet}!A1", safe="!$':")
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        f"{spreadsheet_id}/values/{encoded_range}:append"
    )
    params = {
        "valueInputOption": "USER_ENTERED",
        "insertDataOption": "INSERT_ROWS",
        "includeValuesInResponse": "false",
    }
    payload = {
        "majorDimension": "ROWS",
        "values": values,
    }
    headers_map = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, params=params, headers=headers_map, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise GoogleSheetsExportError(f"google_sheets_append_failed:{exc}") from exc

    updates = body.get("updates", {}) if isinstance(body, dict) else {}
    updated_range = updates.get("updatedRange") if isinstance(updates, dict) else None
    updated_rows_raw = updates.get("updatedRows") if isinstance(updates, dict) else None
    updated_rows = int(updated_rows_raw) if isinstance(updated_rows_raw, int) else None

    return GoogleSheetsExportResult(
        spreadsheet_id=spreadsheet_id,
        sheet_name=safe_sheet,
        updated_range=updated_range if isinstance(updated_range, str) else None,
        updated_rows=updated_rows,
    )

