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
- Backend: FastAPI (next tasks start API bootstrap).
- Queue: Redis + Celery (planned).
- DB: PostgreSQL.
- Storage: local first, S3/R2 later.
- Inference: vLLM, primary `dots.ocr`, fallback `chandra`.

## 4) Environment Notes

Primary env template is `.env.example`.

Important runtime notes for this machine/session:
1. Use `npm.cmd` (not `npm`) due PowerShell script policy behavior.
2. Frontend install/check commands should set local npm cache dirs if permission issues appear.
3. Backend tooling currently avoids third-party package installs and uses stdlib tooling scripts.

## 5) Completed Task Batches

Completed:
1. `T-001` to `T-003`: scope freeze, schemas, repo structure.
2. `T-004` to `T-006`: env template, local setup doc, startup scripts.
3. `T-007` to `T-009`: backend tooling, frontend tooling, API envelope/error contracts.

Task status source of truth: `tasks.md`.

## 6) Next Tasks To Execute

Next in strict order:
1. `T-010` Bootstrap FastAPI app with `/health` and `/ready`.
2. `T-011` Set up PostgreSQL connection and migration framework.
3. `T-012` Implement core tables (`documents`, `jobs`, `extraction_results`).

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

1. `42481fb` Complete tasks `T-007` to `T-009`.
2. `5fce0f4` Complete tasks `T-004` to `T-006`.
3. `142dd7d` Complete tasks `T-001` to `T-003`.
4. `b562fc5` Expand post-MVP roadmap and backlog.
5. `e5cd7ff` Refine PRD + add task backlog + AGENTS context.

## 10) Update Protocol For Future Sessions

After each completed task batch:
1. Update `tasks.md` done rows.
2. Update this `MEMORY.md`:
- completed ranges,
- next three tasks,
- any new caveats or workflow changes.
3. Commit and push.
