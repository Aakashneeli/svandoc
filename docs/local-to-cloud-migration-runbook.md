# Local-to-Cloud Migration Runbook

Last updated: 2026-02-25

This runbook defines how to move svanDoc from local-only runtime to managed cloud dependencies without rewriting application code.

## Goal

Move from:
1. Local API + local worker + local frontend.
2. Local DB/Redis/storage/inference.

To:
1. Same API/worker/frontend code.
2. Managed DB/Redis/storage/inference configured by environment variables only.

## Preconditions

1. `T-057` complete (profile-aware environment overlay).
2. `T-058` complete (storage backend switching already validated).
3. RunPod endpoint operations defined in `docs/runpod-operations-runbook.md`.
4. `.env` exists for local defaults.
5. `.env.staging` exists (copied from `.env.staging.example`) with managed endpoints and secrets.

## Required Staging Variables

At minimum, staging overlay must set:
1. `APP_ENV=staging`
2. `DATABASE_URL`
3. `REDIS_URL`
4. `STORAGE_BACKEND` (`local` for dry-run compatibility, `s3` for cloud-like flow)
5. `NEXT_PUBLIC_API_BASE_URL`
6. `VLLM_BASE_URL`
7. `VLLM_FALLBACK_BASE_URL`
8. `VLLM_API_KEY`
9. `RUNPOD_ENDPOINT_ID_PRIMARY`
10. `RUNPOD_ENDPOINT_ID_FALLBACK`

When `STORAGE_BACKEND=s3`, also set:
1. `S3_BUCKET`
2. `S3_REGION`
3. `S3_ACCESS_KEY_ID`
4. `S3_SECRET_ACCESS_KEY`

## Dry-Run Validation

Use the staged profile dry-run script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/staging-dry-run.ps1 -Profile staging
```

What it checks:
1. Loads `.env` + `.env.<profile>` with profile precedence.
2. Verifies required variables are present.
3. Exports profile values into process env for migration execution.
4. Runs `backend/scripts/migrate.ps1 -ShowCurrent`.
5. Optionally checks API readiness (`/ready`) when API is running.
6. Writes evidence to `.local/staging-dry-run.json`.

If API is not running, run migration-only dry run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/staging-dry-run.ps1 -Profile staging -SkipReadiness
```

## Migration Sequence (Local -> Managed Dependencies)

1. Prepare profile:
   - Copy `.env.staging.example` to `.env.staging`.
   - Fill managed `DATABASE_URL`, `REDIS_URL`, storage, and inference endpoints.
2. Validate config and migration:
   - Run `scripts/staging-dry-run.ps1`.
3. Validate inference endpoints:
   - Run `backend/scripts/inference-smoke.ps1` and confirm `result_code=SMOKE_OK`.
4. Boot stack with staging profile:
   - `$env:APP_ENV="staging"`
   - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1`
5. Execute smoke path:
   - Upload one invoice and one receipt.
   - Wait for job completion/review state.
   - Run JSON/CSV/XLSX export.
6. Confirm observability:
   - `/ready` returns ready.
   - `/metrics` and `/alerts` return expected envelopes.
7. Capture evidence:
   - Save dry-run JSON artifact.
   - Save inference smoke JSON artifact.
   - Save smoke request/response samples for release notes.

## Rollback

1. Stop local services: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-local.ps1`.
2. Set `APP_ENV=local`.
3. Re-run local startup and smoke checks.
4. Keep staging profile file unchanged for next trial.

## Evidence Artifacts

Store these under `.local/` for each dry run:
1. `.local/staging-dry-run.json`
2. `.local-sandbox/inference-smoke.json` (or configured output path)
3. Upload/review/export API smoke logs
4. Any migration logs (when troubleshooting failures)
