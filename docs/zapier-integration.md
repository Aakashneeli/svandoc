# Zapier Integration Guide

This guide covers task `T-065`.

svanDoc supports Zapier with:

1. Trigger: completed jobs.
2. Action: fetch extraction results for a document.

## Prerequisites

1. Configure outbound webhooks (`docs/webhooks.md`) for optional instant trigger flow.
2. Set `ZAPIER_API_KEY` in backend environment.

## Trigger Option A (Polling Trigger)

Use Zapier Webhooks or API Request step to call:

`GET /api/integrations/zapier/triggers/job-completed`

Headers:

`x-zapier-api-key: <ZAPIER_API_KEY>`

Optional query params:

1. `since` (ISO timestamp)
2. `limit` (`1` to `200`, default `50`)

Response includes recent completed jobs (`job_id`, `document_id`, `finished_at`).

## Trigger Option B (Instant Trigger via Webhook)

Subscribe Zapier Catch Hook URL in `WEBHOOK_ENDPOINTS`.

Event:

`job.completed`

Filter by `event_type` in Zapier to route only completed job events.

## Action: Fetch Results

Call:

`GET /api/integrations/zapier/actions/fetch-results?document_id=<id>`

Headers:

`x-zapier-api-key: <ZAPIER_API_KEY>`

Response contains:

1. `document_id`
2. `schema_version`
3. `doc_type`
4. `review_required`
5. `structured_payload`
6. `confidence_map`

## Notes

1. `403 FORBIDDEN` is returned for missing/invalid Zapier key.
2. `404 DOCUMENT_NOT_FOUND` or `404 EXTRACTION_NOT_FOUND` are returned when source data is unavailable.
