# Local Setup Guide (No Docker)

Last updated: 2026-02-22

This guide sets up svanDoc for local-first development on a clean machine.

## 1. Required Software

1. Node.js 20 LTS
2. Python 3.11
3. Supabase project (PostgreSQL-compatible) or local PostgreSQL 16
4. Redis 7
5. Git

## 2. Install Steps (Windows)

### Node.js 20 LTS

1. Install Node.js 20 LTS from the official installer.
2. Verify:

```powershell
node --version
npm --version
```

### Python 3.11

1. Install Python 3.11 and enable "Add Python to PATH".
2. Verify:

```powershell
python --version
pip --version
```

### Supabase Postgres (recommended)

1. Create a Supabase project.
2. Open `Project Settings` -> `Database` -> `Connection string`.
3. Copy the `URI` connection string and set `DATABASE_URL` in `.env`.
4. Ensure `sslmode=require` is present.
5. Verify connectivity by running:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/migrate.ps1
```

### Local PostgreSQL 16 (optional fallback)

1. Install PostgreSQL 16.
2. Create database `svandoc`.
3. Set `.env` `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/svandoc`.
4. Verify:

```powershell
psql --version
psql -U postgres -h localhost -p 5432 -d postgres -c "SELECT version();"
```

### Redis 7

1. Install Redis 7.
2. Start Redis service.
3. Verify:

```powershell
redis-cli ping
```

Expected response: `PONG`

## 3. Project Setup

From repository root:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` if your local credentials/ports differ from defaults.

Minimum local values to verify:

1. `DATABASE_URL`
2. `REDIS_URL`
3. `STORAGE_BACKEND=local`
4. `LOCAL_STORAGE_PATH`
5. `API_PORT` and `FRONTEND_PORT`
6. `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`
7. `VLLM_BASE_URL`, `VLLM_FALLBACK_BASE_URL`, `VLLM_API_KEY`
8. `RUNPOD_ENDPOINT_ID_PRIMARY`, `RUNPOD_ENDPOINT_ID_FALLBACK`
9. `OCR_DEFAULT_MODEL=rednote-hilab/dots.ocr`
10. `OCR_FALLBACK_MODEL=datalab-to/chandra`
11. `ALERT_FAILED_RECENT_THRESHOLD`, `ALERT_QUEUE_BACKLOG_DEPTH`, `ALERT_API_ERROR_RATE_THRESHOLD`
12. `RATE_LIMIT_ENABLED`, `RATE_LIMIT_WINDOW_SECONDS`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_UPLOAD_MAX_REQUESTS`, `RATE_LIMIT_BLOCK_SECONDS`
13. Keep `VLLM_API_KEY` out of git; store only in untracked `.env` and cloud secret managers.

## 4. Startup

Use one-command startup script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Stop all services:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

## 5. Clean Machine Validation Checklist

Run these checks in order:

1. `node --version` returns Node 20.x
2. `python --version` returns Python 3.11.x
3. `psql --version` returns PostgreSQL 16.x
4. `redis-cli ping` returns `PONG`
5. `Copy-Item .env.example .env` succeeds
6. `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1` starts API, worker, and frontend processes
7. `Invoke-WebRequest http://localhost:8000` returns HTTP response
8. `Invoke-WebRequest http://localhost:3000` returns HTTP response
9. `powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1` stops all local service processes

If all checks pass, local setup is ready for the next implementation tasks.

## 6. Supabase Migration Validation Checklist

Run this when validating a new Supabase environment:

1. Set `.env` `DATABASE_URL` to your Supabase URI with `sslmode=require`.
2. Run `powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/migrate.ps1`.
3. Run `myvenv\Scripts\python.exe -m alembic -c backend\alembic.ini current` from repo root.
4. Confirm output revision is `20260214_0004` (or newer if additional migrations were added).

## 7. Inference Environment Contract (RunPod First)

Use this canonical RunPod contract for default OCR runtime:

1. Primary endpoint URL: `VLLM_BASE_URL=https://api.runpod.ai/v2/<primary-endpoint-id>/openai/v1`
2. Fallback endpoint URL: `VLLM_FALLBACK_BASE_URL=https://api.runpod.ai/v2/<fallback-endpoint-id>/openai/v1`
3. API auth secret: `VLLM_API_KEY=<runpod-api-token>`
4. Optional endpoint IDs: `RUNPOD_ENDPOINT_ID_PRIMARY`, `RUNPOD_ENDPOINT_ID_FALLBACK`
5. Primary model ID: `OCR_DEFAULT_MODEL=rednote-hilab/dots.ocr`
6. Fallback model ID: `OCR_FALLBACK_MODEL=datalab-to/chandra`
7. Keep model IDs as upstream canonical Hugging Face IDs; treat quantized/community forks as optional overrides.

Development-only local inference fallback (not default, not production):

1. `VLLM_BASE_URL=http://localhost:11434/v1`
2. `VLLM_FALLBACK_BASE_URL=http://localhost:11435/v1`
3. `VLLM_API_KEY=` (empty for local server)
4. Use this path only when intentionally validating local model serving behavior.

Detailed fallback provisioning steps:

1. `docs/inference-model-setup.md`

Inference smoke validation command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/inference-smoke.ps1
```

## 8. Staging Profile (Managed Supabase + Redis)

For staging profile-based startup (no code changes):

1. Copy `.env.staging.example` to `.env.staging`.
2. Set real `DATABASE_URL` and `REDIS_URL` for managed services.
3. Set PowerShell env var before startup:

```powershell
$env:APP_ENV="staging"
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

When `APP_ENV=staging`, startup scripts load base `.env` values and overlay values from `.env.staging` (or `.env.staging.example` if `.env.staging` is not present).
