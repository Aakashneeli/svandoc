# svanDoc Memory File

Last updated: 2026-02-15 (T-023 complete)
Purpose: fast context restore in new sessions without full repo re-scan.

## 1) Project Intent

- Build an SME-focused document extraction product.
- MVP focus: invoice and receipt extraction only.
- Core flow: upload -> process -> review -> export.
- Payment/subscription is intentionally deferred.

## 2) Scope Guardrails

In scope now:
1. Invoice/receipt OCR + structured extraction.
2. Human review and correction for low-confidence fields.
3. Export to JSON/CSV/XLSX.
4. Local-first development workflow.

Out of scope now:
1. Billing/payments.
2. ERP and broad connector implementation.
3. Healthcare-specific specialization.

## 3) Current Architecture Decisions

- Frontend: Next.js + TypeScript (scaffold in progress).
- Backend: FastAPI app bootstrap completed with `/health`, `/ready`, and `POST /api/documents/upload`.
- Backend DB layer: SQLAlchemy engine/session bootstrap + Alembic migration framework added.
- Queue: Redis + Celery integration implemented with enqueue + local eager-consumption tests.
- DB: Supabase Postgres (PostgreSQL-compatible) via `DATABASE_URL`; SQLAlchemy + Alembic retained.
- Storage: local first, S3/R2 later.
- Inference: vLLM, primary `dots.ocr`, fallback `chandra`.

## 4) Environment Notes

Primary env template is `.env.example`.

Important runtime notes for this machine/session:
1. Use `npm.cmd` (not `npm`) due PowerShell script policy behavior.
2. Frontend install/check commands should set local npm cache dirs if permission issues appear.
3. Create and use repo venv `myvenv` before backend package installs.
4. Backend scripts auto-prefer `myvenv\Scripts\python.exe` when present.
5. Readiness now checks both DB and Redis; `/ready` returns `503 DEPENDENCY_UNAVAILABLE` on dependency failures.
6. `python-multipart` is required for upload endpoint form parsing and is now pinned in backend dependencies.
7. Use `uv` for Python dependency management (`uv pip install -r <requirements-file>`); set `UV_CACHE_DIR` under repo-local paths if default cache permissions fail.
8. Supabase hostnames (`*.supabase.co`) get `sslmode=require` automatically if not provided in `DATABASE_URL`.
9. Use Supabase pooler/IPv4-capable `DATABASE_URL` for this environment; direct DB host may fail due to IPv6-only resolution.

## 5) Completed Task Batches

Completed:
1. `T-001` to `T-003`: scope freeze, schemas, repo structure.
2. `T-004` to `T-006`: env template, local setup doc, startup scripts.
3. `T-007` to `T-009`: backend tooling, frontend tooling, API envelope/error contracts.
4. `T-010` to `T-012`: FastAPI bootstrap endpoints, PostgreSQL/Alembic framework, and core tables (`documents`, `jobs`, `extraction_results`) with constraints/indexes.
5. `T-013` to `T-015`: `user_corrections`/`export_artifacts` tables + migration, upload endpoint, and file validation (type/size/page count) with structured errors.
6. `T-016` to `T-018`: storage backend abstraction (`local` + `s3` stub), checksum duplicate detection/conflict handling, and Redis/Celery queue integration with local consumption tests.
7. `T-019` to `T-020`: job lifecycle state machine + DB transition enforcement and worker structured logging context (`request_id`, `job_id`, `document_id`).
8. `T-021`: image preprocessing module added (orientation correction, denoise, deskew) with sample-corpus tests.
9. `T-022`: vLLM client module added with timeout, retry/backoff policy, and metrics hooks.
10. `T-023`: `dots.ocr` adapter integrated in worker path with extraction persistence to `extraction_results`.
11. `T-098` to `T-099`: Supabase-first DB runtime/env/docs updates (URL normalization, SSL defaults, pool settings, setup docs).
12. `T-100`: Alembic migration validation completed against Supabase-managed Postgres.
13. `T-101`: readiness dependency checks for DB + Redis with failure envelopes and tests.

Task status source of truth: `tasks.md`.

## 6) Next Tasks To Execute

Next in strict order:
1. `T-024` Integrate `Chandra` fallback extraction adapter.
2. `T-025` Implement routing rules from `dots.ocr` to fallback.
3. `T-026` Normalize raw OCR output into canonical schema.
4. Deployment tasks `T-102` to `T-105` are intentionally deferred until after core MVP extraction flow progress.

Execution rule:
1. Implement in order.
2. Test each task thoroughly.
3. Mark each completed task row as done in `tasks.md`.
4. Update `MEMORY.md` after each completed task.
5. Commit and push after each completed task.

## 7) Key Files To Read First

1. `MEMORY.md` (this file).
2. `tasks.md` (current pending task order and definitions of done).
3. `PRD.md` (product and technical requirements).
4. `AGENTS.md` (agent operating constraints for this repo).

## 8) Validation Commands Reference

Backend checks:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/setup-dev.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/format.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/lint.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/migrate.ps1
```

Frontend checks:
```powershell
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run test
```

Contracts checks:
```powershell
python contracts/api/validate_examples.py
```

Local startup checks:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

## 9) Recent Commits (for context)

1. `a0d318e` Complete task `T-020` worker skeleton structured logging context.
2. `9618532` Complete task `T-019` enforce job lifecycle transitions.
3. `4ceed0e` Complete task `T-018` integrate Redis and Celery queue.
4. `3ca16f1` Complete task `T-017` duplicate detection by checksum.
5. `656eb48` Complete task `T-016` storage abstraction interface.

## 10) Validation Notes From Latest Cycle

1. `T-013` migration/schema checks passed against local SQLite (includes `user_corrections` and `export_artifacts` tables, indexes, and constraints).
2. `T-014` upload endpoint tests passed for single and batch uploads with DB persistence and local file writes.
3. `T-015` validation tests passed for unsupported type, oversize upload, and page-limit rejection with structured `VALIDATION_ERROR` envelope.
4. Attempt to run migration against PostgreSQL (`localhost:5432`) still failed with connection timeout because local Postgres was unavailable.
5. `T-016` storage abstraction tests passed for `local` and `s3` stub backends, with upload endpoint coverage for both modes.
6. `T-017` duplicate detection tests passed for duplicate-in-request and already-existing-checksum conflict paths (`409 DUPLICATE_DOCUMENT`).
7. `T-018` queue integration tests passed with Celery eager mode, validating enqueue + local task consumption and job status progression (`queued` -> `processing` -> `completed`).
8. `T-019` transition enforcement tests passed in both code and DB (trigger-based restriction of invalid status changes).
9. `T-020` worker logging tests passed for structured context keys (`request_id`, `job_id`, `document_id`) and request-id propagation from upload enqueue.
10. `T-098`, `T-099`, and `T-101` changes passed backend suite (`41` tests) on `2026-02-15`.
11. `T-100` migration validation succeeded against Supabase Postgres (`20260214_0004` head) using pooled connection settings.
12. `T-021` preprocessing tests passed on generated sample corpus (clean/noisy/skewed) and full backend suite (`44` tests) on `2026-02-15`.
13. `T-022` vLLM client retry policy tests passed (timeouts, `503`, non-retryable `400`) and full backend suite (`48` tests) on `2026-02-15`.
14. `T-023` `dots.ocr` adapter and worker integration tests passed (including extraction persistence + review-required branching) and full backend suite (`51` tests) on `2026-02-15`.

## 11) Update Protocol For Future Sessions

After each completed task:
1. Update `tasks.md` done rows.
2. Update this `MEMORY.md`:
- completed ranges,
- next three tasks,
- any new caveats or workflow changes.
3. Commit and push.
