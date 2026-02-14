# API Envelope and Error Contract

This directory defines the canonical API response structure shared by backend endpoints.

## Response envelope

Every JSON response must follow this envelope:

```json
{
  "status": "success | error",
  "request_id": "req_...",
  "timestamp": "ISO-8601 datetime",
  "data": {},
  "error": null,
  "meta": {}
}
```

Rules:

1. `status=success`:
- `data` must be present (object or array).
- `error` must be `null`.

2. `status=error`:
- `error` must be present.
- `data` must be `null`.

3. `request_id` is required for traceability and support/debug workflows.
4. `timestamp` is required in UTC date-time format.

## Error object

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Human-readable summary",
  "details": {},
  "retryable": false
}
```

Required fields:

1. `code`: machine-friendly stable error identifier.
2. `message`: user-facing summary.
3. `retryable`: if client can safely retry.

Optional:

1. `details`: structured context (field errors, dependency errors, etc.).

## HTTP mapping guidance

1. `200/201`: success envelope
2. `400`: validation/client input errors
3. `401/403`: auth and permission errors
4. `404`: resource not found
5. `409`: conflict/idempotency errors
6. `429`: rate limit errors
7. `500/502/503`: server/dependency failures

## Upload duplicate behavior

`POST /api/documents/upload` returns `409` with `code=DUPLICATE_DOCUMENT` when:

1. The same file content appears more than once in a single request.
2. The uploaded file checksum already exists in `documents`.
