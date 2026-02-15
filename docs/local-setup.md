# Local Setup Guide (No Docker)

Last updated: 2026-02-15

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
7. `VLLM_BASE_URL`, `VLLM_FALLBACK_BASE_URL`
8. `OCR_DEFAULT_MODEL=rednote-hilab/dots.ocr`
9. `OCR_FALLBACK_MODEL=datalab-to/chandra`
10. `ALERT_FAILED_RECENT_THRESHOLD`, `ALERT_QUEUE_BACKLOG_DEPTH`, `ALERT_API_ERROR_RATE_THRESHOLD`
11. `RATE_LIMIT_ENABLED`, `RATE_LIMIT_WINDOW_SECONDS`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_UPLOAD_MAX_REQUESTS`, `RATE_LIMIT_BLOCK_SECONDS`

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

## 7. Inference Environment Contract

Use this canonical local inference contract before OCR pipeline tasks:

1. Primary endpoint: `VLLM_BASE_URL=http://localhost:11434/v1`
2. Fallback endpoint: `VLLM_FALLBACK_BASE_URL=http://localhost:11435/v1`
3. Primary model ID: `OCR_DEFAULT_MODEL=rednote-hilab/dots.ocr`
4. Fallback model ID: `OCR_FALLBACK_MODEL=datalab-to/chandra`
5. Keep model IDs as upstream canonical Hugging Face IDs; treat quantized/community forks as optional overrides.

Detailed provisioning steps:

1. `docs/inference-model-setup.md`

Inference smoke validation command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/inference-smoke.ps1
```

