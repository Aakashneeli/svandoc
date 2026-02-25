# Backend Package

This package will host the FastAPI application.

## Planned responsibilities

1. Document upload and metadata endpoints.
2. Job orchestration and status endpoints.
3. Extraction read/update endpoints.
4. Export endpoints and artifact tracking.

## Planned stack

- Python 3.11
- FastAPI
- Supabase Postgres (PostgreSQL-compatible)
- Redis (queue integration)

## Developer tooling

Commands:

```powershell
uv pip install -r backend/requirements-dev.txt
powershell -ExecutionPolicy Bypass -File backend/scripts/setup-dev.ps1
powershell -ExecutionPolicy Bypass -File backend/scripts/lint.ps1
powershell -ExecutionPolicy Bypass -File backend/scripts/test.ps1
powershell -ExecutionPolicy Bypass -File backend/scripts/migrate.ps1
```

`backend/scripts/test.ps1` defaults to module-level timeout execution to avoid
indefinite hangs in unstable runtimes. Optional overrides:

- `BACKEND_TEST_RUN_MODE=discover` to run raw `unittest discover`.
- `BACKEND_TEST_MODULE_TIMEOUT_SECONDS=<seconds>` to tune per-module timeout.
- `BACKEND_TEST_MODULE_FILTER=<fnmatch>` for targeted module runs.

Optional formatter:

```powershell
powershell -ExecutionPolicy Bypass -File backend/scripts/format.ps1
```

Tooling uses Python scripts in `backend/tools/` and FastAPI-related dependencies listed in
`backend/requirements-dev.txt`.

## Current status

1. FastAPI health/readiness and upload endpoints are implemented.
2. PostgreSQL-compatible models and Alembic migrations are in place for core entities.
3. Uploads enqueue Celery jobs when `QUEUE_BACKEND=celery`.

## Supabase Notes

1. Set `DATABASE_URL` to the Supabase Postgres URI (`sslmode=require`).
2. Migration command: `powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/migrate.ps1`.
3. Verify migration revision: `myvenv\Scripts\python.exe -m alembic -c backend\alembic.ini current`.

## Inference Notes

1. RunPod-first primary OCR endpoint: `VLLM_BASE_URL` and model `OCR_DEFAULT_MODEL`.
2. RunPod-first fallback OCR endpoint: `VLLM_FALLBACK_BASE_URL` and model `OCR_FALLBACK_MODEL`.
3. RunPod auth secret: `VLLM_API_KEY` (keep in untracked env or managed secret store).
4. Optional RunPod endpoint IDs for ops: `RUNPOD_ENDPOINT_ID_PRIMARY`, `RUNPOD_ENDPOINT_ID_FALLBACK`.
5. Canonical upstream model IDs:
   - `rednote-hilab/dots.ocr`
   - `datalab-to/chandra`
6. Local vLLM endpoint overrides are development-only fallback and not production default.
7. Validate dual-endpoint inference setup:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/inference-smoke.ps1`
8. Hosted inference retry policy envs:
   - `VLLM_TIMEOUT_SECONDS`, `VLLM_MAX_RETRIES`, `VLLM_RETRY_BACKOFF_SECONDS`, `VLLM_RETRY_MAX_BACKOFF_SECONDS`
9. Queue fail-closed retry/dead-letter policy envs:
   - `PROCESSING_MAX_RETRIES`, `PROCESSING_RETRY_BACKOFF_SECONDS`
10. RunPod ops reference:
   - `docs/runpod-operations-runbook.md`
11. Deploy readiness gate command:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/runpod-readiness-gate.ps1`
