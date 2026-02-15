# Outbound Webhooks

This document defines svanDoc outbound webhook behavior for task `T-064`.

## Emitted Events

1. `job.completed`
2. `job.failed`
3. `export.created`

## Configuration

Set these variables in `.env`:

1. `WEBHOOK_ENDPOINTS`: comma-separated endpoint URLs.
2. `WEBHOOK_SIGNING_SECRET`: shared secret used for HMAC signing.
3. `WEBHOOK_MAX_ATTEMPTS`: max attempts per endpoint (default `3`).
4. `WEBHOOK_TIMEOUT_SECONDS`: request timeout in seconds (default `5`).
5. `WEBHOOK_RETRY_BACKOFF_SECONDS`: exponential backoff base in seconds (default `2`).

If `WEBHOOK_ENDPOINTS` or `WEBHOOK_SIGNING_SECRET` is missing, webhook delivery is skipped.

## Request Contract

Each delivery is `POST` with `Content-Type: application/json`.

Headers:

1. `X-SvanDoc-Event`: event type.
2. `X-SvanDoc-Event-Id`: stable event UUID.
3. `X-SvanDoc-Signature`: `sha256=<hex-hmac>` computed from raw request body.

Payload shape:

```json
{
  "event_id": "uuid",
  "event_type": "job.completed",
  "occurred_at": "2026-02-15T00:00:00Z",
  "data": {}
}
```

## Delivery Logs

Each delivery attempt is written to `webhook_delivery_logs` with:

1. endpoint URL
2. event type and event id
3. attempt number
4. delivery status (`delivered` or `failed`)
5. HTTP status code or error message
6. payload and signature used for delivery
