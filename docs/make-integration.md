# Make.com Integration Guide

This guide covers task `T-066`.

svanDoc publishes reusable Make.com scenario templates for:

1. Upload + job status polling workflow.
2. Completed job -> extraction fetch -> export workflow.

## Configuration

Set backend environment variables:

1. `MAKE_API_KEY`: required for Make template endpoint access.
2. `MAKE_API_BASE_URL` (optional): base URL inserted into generated template module URLs.

## Fetch Templates

Call:

`GET /api/integrations/make/templates`

Headers:

`x-make-api-key: <MAKE_API_KEY>`

Response returns `templates[]`, each with:

1. `id`
2. `name`
3. `description`
4. `modules[]`
5. `expected_outcome`

## Template Coverage

Template `upload_to_status_polling`:

1. `POST /api/documents/upload`
2. Iterate `job_ids`
3. `GET /api/jobs/{job_id}`

Template `completed_job_to_export`:

1. Receive `job.completed` webhook event
2. `GET /api/documents/{document_id}/extraction`
3. `POST /api/documents/{document_id}/export`

## Connection Notes

1. For instant trigger flow, add Make webhook URL to `WEBHOOK_ENDPOINTS`.
2. Use `x-user-role` headers (`viewer`/`editor`) in HTTP modules where required.
3. Use scenario retries for transient `429` and `5xx` responses.
