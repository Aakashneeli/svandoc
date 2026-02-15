# API Rate Limiting and Abuse Guardrails

Last updated: 2026-02-15

Rate limiting is enforced for `"/api/*"` routes.

## Rules

1. Per-subject request limit
- Subject key priority: `x-user-id` -> `x-forwarded-for` -> client IP.
- Window: `RATE_LIMIT_WINDOW_SECONDS` (default `60`).
- Limits:
  - General API requests: `RATE_LIMIT_MAX_REQUESTS` (default `300`)
  - Upload endpoint (`/api/documents/upload`): `RATE_LIMIT_UPLOAD_MAX_REQUESTS` (default `30`)

2. Abuse block
- If requests exceed the limit by a burst margin, requests are blocked with `ABUSE_BLOCKED`.
- Block duration: `RATE_LIMIT_BLOCK_SECONDS` (default `300`).

## Response Behavior

When blocked, API responds with `429` and:

1. Envelope error code: `RATE_LIMITED` or `ABUSE_BLOCKED`
2. `Retry-After` header
3. Error details:
- `reason`
- `retry_after_seconds`
- `subject`

## Validation

Run focused tests:

```powershell
$env:PYTHONPATH="backend/src"; myvenv\Scripts\python.exe -m unittest backend/tests/test_rate_limit.py
```
