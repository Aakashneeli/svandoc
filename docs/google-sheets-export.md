# Google Sheets Export Connector

Last updated: 2026-02-15

svanDoc supports direct export from review flow to a selected Google Sheet.

## API

`POST /api/documents/{id}/export` with:

```json
{
  "format": "gsheets",
  "google_spreadsheet_id": "spreadsheet-id",
  "google_sheet_name": "Sheet1",
  "google_access_token": "oauth-access-token"
}
```

Required fields for `gsheets`:
1. `google_spreadsheet_id`
2. `google_access_token`

Optional:
1. `google_sheet_name` (defaults to `Sheet1`)

## Behavior

1. Backend converts canonical extraction payload into deterministic tabular row.
2. Connector appends header + row into the target sheet via Google Sheets API.
3. Export artifact is persisted with:
   - `format = gsheets`
   - `storage_uri = gsheets://<spreadsheet_id>/<sheet_name>`

## Failure Envelope

If Google API delivery fails:
1. Response code: `502`
2. Error code: `EXPORT_DELIVERY_FAILED`
3. `details.connector = google_sheets`

