# Audit Log Views

Last updated: 2026-02-15

Audit history is available per document for:

1. Extraction corrections (`user_corrections`)
2. Export events (`export_artifacts`)

## Backend Endpoint

`GET /api/documents/{document_id}/audit`

Response data shape:

1. `document_id`
2. `corrections[]`:
- `id`, `field_path`, `old_value`, `new_value`, `corrected_by`, `corrected_at`
3. `exports[]`:
- `id`, `format`, `storage_uri`, `created_by`, `created_at`

## Frontend View

The review page now shows an **Audit History** panel with:

1. Recent correction events
2. Recent export events

The panel refreshes after successful correction saves and export actions.
