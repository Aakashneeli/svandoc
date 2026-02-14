# svanDoc Memory File

Last updated: 2026-02-14
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
- Queue: Redis + Celery (planned).
- DB: PostgreSQL.
- Storage: local first, S3/R2 later.
- Inference: vLLM, primary `dots.ocr`, fallback `chandra`.

## 4) Environment Notes

Primary env template is `.env.example`.

Important runtime notes for this machine/session:
1. Use `npm.cmd` (not `npm`) due PowerShell script policy behavior.
2. Frontend install/check commands should set local npm cache dirs if permission issues appear.
3. Create and use repo venv `myvenv` before backend package installs.
4. Backend scripts auto-prefer `myvenv\Scripts\python.exe` when present.
5. Local PostgreSQL on `localhost:5432` was not reachable in this session (`connection timeout`).
6. `python-multipart` is required for upload endpoint form parsing and is now pinned in backend dependencies.

## 5) Completed Task Batches

Completed:
1. `T-001` to `T-003`: scope freeze, schemas, repo structure.
2. `T-004` to `T-006`: env template, local setup doc, startup scripts.
3. `T-007` to `T-009`: backend tooling, frontend tooling, API envelope/error contracts.
4. `T-010` to `T-012`: FastAPI bootstrap endpoints, PostgreSQL/Alembic framework, and core tables (`documents`, `jobs`, `extraction_results`) with constraints/indexes.
5. `T-013` to `T-015`: `user_corrections`/`export_artifacts` tables + migration, upload endpoint, and file validation (type/size/page count) with structured errors.

Task status source of truth: `tasks.md`.

## 6) Next Tasks To Execute

Next in strict order:
1. `T-016` Implement storage abstraction interface (`local`, `s3`).
2. `T-017` Add checksum generation and duplicate detection.
3. `T-018` Integrate Redis and Celery queue.

Execution rule:
1. Implement in order.
2. Test each task thoroughly.
3. Mark each task row as done in `tasks.md`.
4. Commit and push after each 3-task cycle.

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

1. `ef296e9` Complete task `T-014` document upload endpoint.
2. `58e396c` Complete tasks `T-010` to `T-013` backend API/db foundations.
3. `49651aa` Add `MEMORY.md` for fast session context and link it in AGENTS.
4. `42481fb` Complete tasks `T-007` to `T-009`.
5. `5fce0f4` Complete tasks `T-004` to `T-006`.

## 10) Validation Notes From Latest Cycle

1. `T-013` migration/schema checks passed against local SQLite (includes `user_corrections` and `export_artifacts` tables, indexes, and constraints).
2. `T-014` upload endpoint tests passed for single and batch uploads with DB persistence and local file writes.
3. `T-015` validation tests passed for unsupported type, oversize upload, and page-limit rejection with structured `VALIDATION_ERROR` envelope.
4. Attempt to run migration against PostgreSQL (`localhost:5432`) still failed with connection timeout because local Postgres was unavailable.

## 11) Update Protocol For Future Sessions

After each completed task batch:
1. Update `tasks.md` done rows.
2. Update this `MEMORY.md`:
- completed ranges,
- next three tasks,
- any new caveats or workflow changes.
3. Commit and push.
