# Alert Thresholds

Last updated: 2026-02-15

This project exposes threshold-based operational alerts at `GET /alerts` and includes alert status in `GET /metrics`.

## Alert Rules

1. `REPEATED_JOB_FAILURES` (high)
- Trigger: `jobs.failed_recent_window >= ALERT_FAILED_RECENT_THRESHOLD`
- Default threshold: `5`

2. `QUEUE_BACKLOG` (medium)
- Trigger: `queue.depth >= ALERT_QUEUE_BACKLOG_DEPTH`
- Default threshold: `25`

3. `API_ERROR_RATE_HIGH` (medium)
- Trigger: `api.error_rate >= ALERT_API_ERROR_RATE_THRESHOLD`
- Default threshold: `0.2`

## Environment Variables

Set these in `.env`:

```env
ALERT_FAILED_RECENT_THRESHOLD=5
ALERT_QUEUE_BACKLOG_DEPTH=25
ALERT_API_ERROR_RATE_THRESHOLD=0.2
```

## Trigger Validation

Run backend tests that explicitly trigger alerts:

```powershell
myvenv\Scripts\python.exe -m unittest backend/tests/test_alerts.py
```
