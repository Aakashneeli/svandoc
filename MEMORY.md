# svanDoc Memory File

Last updated: 2026-02-15 (updated after T-067)
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

- Frontend: Next.js + TypeScript app shell implemented with base navigation/routes.
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
10. Inference provisioning is now explicitly tracked before routing: complete `T-106` to `T-109` before `T-025`.
11. Canonical model IDs are `rednote-hilab/dots.ocr` (primary) and `datalab-to/chandra` (fallback), with dual endpoints `VLLM_BASE_URL` and `VLLM_FALLBACK_BASE_URL`.
12. Outbound webhook delivery is controlled by `WEBHOOK_ENDPOINTS`, `WEBHOOK_SIGNING_SECRET`, and retry vars (`WEBHOOK_MAX_ATTEMPTS`, `WEBHOOK_TIMEOUT_SECONDS`, `WEBHOOK_RETRY_BACKOFF_SECONDS`).

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
11. `T-024`: `Chandra` fallback adapter integrated with callable worker path for difficult samples.
12. `T-106`: canonical OCR model IDs and dual-endpoint env contract pinned in `.env.example`/docs.
13. `T-107`: backend runtime now selects primary vs fallback vLLM endpoint by model path, with tested failure handling.
14. `T-108`: local inference provisioning runbook added for Hugging Face auth + dual vLLM model serving.
15. `T-109`: inference smoke validator added (dual endpoint checks + per-model completion evidence output).
16. `T-025`: worker routing now escalates from primary `dots.ocr` to fallback `chandra` on low-confidence/review-required or complex-layout thresholds.
17. `T-026`: canonical normalization layer added to emit schema-compatible invoice/receipt payloads with required fields/defaults before persistence.
18. `T-027`: field-level confidence map generator added and now persisted for all extractable canonical fields with overall score.
19. `T-028`: normalization validation rules added for totals/date/currency consistency with actionable warnings and review-required escalation.
20. `T-029`: extraction persistence finalized with canonical schema version (`1.0.0`) and synchronized review flags/confidence in DB rows.
21. `T-030`: `GET /api/jobs/{job_id}` endpoint added with status/attempt/timestamps/error details and `JOB_NOT_FOUND` handling.
22. `T-031`: `GET /api/documents/{id}/extraction` endpoint added with structured payload, confidence map, and explicit `DOCUMENT_NOT_FOUND`/`EXTRACTION_NOT_FOUND` handling.
23. `T-032`: `PATCH /api/documents/{id}/extraction` endpoint added with strict field-path updates, correction audit persistence (`user_corrections`), and actor/timestamp tracking.
24. `T-033`: JSON export service added with canonical payload validation and deterministic JSON output generation.
25. `T-034`: CSV export service added with deterministic header ordering and stable value serialization for invoice/receipt canonical payloads.
26. `T-035`: XLSX export service added using `openpyxl`, including typed numeric/date cells and worksheet output compatible with Excel.
27. `T-036`: `POST /api/documents/{id}/export` endpoint added for `json`/`csv`/`xlsx`, with storage write + `export_artifacts` persistence and not-found/validation error handling.
28. `T-037`: Next.js app shell added with shared auth-ready layout and base routes (`/`, `/upload`, `/documents`, `/review`) plus route smoke checks.
29. `T-038`: Upload page implemented with single-file and batch selectors, per-file status tracking (`queued`/`uploading`/`completed`/`failed`), and submit flow to `POST /api/documents/upload`.
30. `T-039`: Documents page implemented with vendor/file/id search, status filter, date-range filtering, and client-side filtered result list.
31. `T-040`: Review page implemented with side-by-side document panel + extracted payload panel, including extraction loading via `GET /api/documents/{id}/extraction`.
32. `T-041`: Inline edit controls added for primitive extraction fields with per-field save actions wired to `PATCH /api/documents/{id}/extraction`, and UI state refresh after corrections.
33. `T-042`: Confidence UI added with threshold control, low-confidence-only filtering, and row-level highlighting tied to `confidence_map.fields` plus review-required visibility.
34. `T-043`: Export actions added to review page for `json`/`csv`/`xlsx`, including per-format run status, artifact messages, and download link rendering from export responses.
35. `T-044`: Frontend validation hints and error banners added across upload/review flows, including user-friendly mapping of backend validation/duplicate errors.
36. `T-045`: Automated backend smoke test added for upload -> review -> export path, covering upload, extraction retrieval, correction patching, and JSON/CSV/XLSX export artifact generation in one flow.
37. `T-046`: Versioned benchmark dataset curated at `datasets/benchmark/v1` with synthetic invoice/receipt samples across clean/noisy/rotated/multilayout variants (PNG+PDF), manifest with checksums, and integrity test coverage.
38. `T-047`: Extraction quality evaluation module added (`svandoc_backend.quality_eval`) with field-level precision/recall/F1 output grouped by document type, benchmark ground truth labels, CLI wrapper (`backend/scripts/quality-eval.ps1`), and evaluator unit tests.
39. `T-048`: Quality regression thresholds enforced in CI via new quality gate module (`svandoc_backend.quality_gate`), CI baseline predictions fixture (`datasets/benchmark/v1/ci_predictions.json`), and GitHub Actions workflow (`.github/workflows/backend-quality-gate.yml`) that runs evaluator + threshold checks.
40. `T-049`: Queue retry/dead-letter handling added in worker processing with bounded retry scheduling/backoff and dead-letter terminal failures, plus integration coverage for retryable timeout requeue and exhausted-retry dead-letter outcomes.
41. `T-050`: Role-based authorization checks added for API endpoints with `admin`/`editor`/`viewer` policy enforcement (`x-user-role`) and explicit `403 FORBIDDEN` responses for invalid or unauthorized roles.
42. `T-051`: Configurable document retention cleanup added with hard-delete execution and persisted audit trail (`document_deletion_events`), plus retention CLI wrapper (`backend/scripts/retention-cleanup.ps1`) and migration `20260215_0005`.
43. `T-052`: Structured logging sink configuration added (`STRUCTURED_LOG_SINK_PATH`) for API/worker logs, request-correlation middleware now sets/echoes `x-request-id` and logs request lifecycle events, and envelope request IDs now consistently use middleware correlation context.
44. `T-053`: In-process metrics instrumentation added with `/metrics` endpoint exposing API request/error/latency metrics, queue depth snapshots, and worker job outcome counters (`processed`, `failed`, `review_required`).
45. `T-054`: Alert threshold evaluation added for repeated failures, queue backlog, and API error rate (`/alerts` + embedded alerts in `/metrics`) with env-configurable thresholds and tests.
46. `T-055`: API rate limiting and abuse guardrails added for `/api/*` routes with per-subject windowed limits, upload-specific threshold, structured `429` responses (`RATE_LIMITED`/`ABUSE_BLOCKED`), and `Retry-After` support.
47. `T-056`: Document audit-log view support added via `GET /api/documents/{id}/audit` (correction + export event history), with review-page UI panel showing correction/export timelines and refresh-on-save/export behavior.
48. `T-057`: Staging config profile support added with `.env.staging.example` and profile-aware environment loading in `scripts/lib/env.ps1` (`.env.<profile>` overlay) enabling config-only swap between local and staging.
49. `T-058`: Storage backend switch integration coverage added to run the same upload + export path under both `local` and `s3` stub backends, verifying persisted URIs/artifacts across both modes.
50. `T-059`: Local-to-cloud migration runbook added (`docs/local-to-cloud-migration-runbook.md`) with profile-based staging dry-run validator (`scripts/staging-dry-run.ps1`) that checks required config, executes migrations, and emits evidence at `.local/staging-dry-run.json`.
51. `T-060`: Pilot workflow metrics package added with anonymized pilot cohort dataset (`datasets/pilot/v1/pilot_sessions.csv`), evaluator module/CLI (`svandoc_backend.pilot_metrics`, `backend/scripts/pilot-metrics.ps1`), and pilot outcome report (`docs/pilot-report-2026-02-15.md`) including completion and time-to-value metrics.
52. `T-061`: Beta feedback prioritization workflow added with scored input dataset (`datasets/pilot/v1/feedback_items.json`), ranking module/CLI (`svandoc_backend.feedback_prioritization`, `backend/scripts/feedback-prioritize.ps1`), and ranked v1.1 hardening backlog (`docs/v1.1-hardening-backlog.md`) with impact/effort/frequency scoring and owners.
53. `T-062`: Google Sheets direct export connector implemented end-to-end with backend connector service (`svandoc_backend.google_sheets_export`), export endpoint support (`format=gsheets` with OAuth token + spreadsheet target), schema migration `20260215_0006`, frontend review-page connector controls, and connector runbook (`docs/google-sheets-export.md`).
54. `T-063`: Cloud storage connectors implemented for Google Drive, OneDrive, and Dropbox (`svandoc_backend.cloud_connectors`) with export endpoint support (`format=gdrive|onedrive|dropbox`), persisted delivery status tracking in `export_artifacts` (`delivery_status`), migration `20260215_0007`, review UI actions, and connector runbook (`docs/cloud-storage-connectors.md`).
55. `T-064`: Outbound webhook events implemented for `job.completed`, `job.failed`, and `export.created` with signed payloads, retry/backoff delivery, per-attempt DB logs (`webhook_delivery_logs`), migration `20260215_0008`, and runbook (`docs/webhooks.md`).
56. `T-065`: Zapier integration added with API-key protected trigger/action endpoints (`/api/integrations/zapier/triggers/job-completed`, `/api/integrations/zapier/actions/fetch-results`) plus setup guide (`docs/zapier-integration.md`) and env contract (`ZAPIER_API_KEY`).
57. `T-066`: Make.com integration templates added via API (`/api/integrations/make/templates`) with API-key protection, reusable upload/export scenario definitions (`svandoc_backend.make_templates`), and setup guide (`docs/make-integration.md`).
58. `T-067`: QuickBooks Online connector added for export sync (`format=quickbooks`) with canonical invoice/receipt mapping (`svandoc_backend.quickbooks_connector`), export endpoint integration, migration `20260215_0009`, and runbook (`docs/quickbooks-connector.md`).
22. `T-098` to `T-099`: Supabase-first DB runtime/env/docs updates (URL normalization, SSL defaults, pool settings, setup docs).
23. `T-100`: Alembic migration validation completed against Supabase-managed Postgres.
24. `T-101`: readiness dependency checks for DB + Redis with failure envelopes and tests.

Task status source of truth: `tasks.md`.

## 6) Next Tasks To Execute

Next in strict order:
1. `T-068` Implement Xero connector with sync status and retry handling.
2. `T-069` Implement phased Sage/Tally connector strategy.
3. `T-070` Implement email intake with workspace-specific ingestion address.
4. `T-071` Launch public REST API with API keys and scoped permissions.
5. Deployment tasks `T-102` to `T-105` are intentionally deferred until after core MVP extraction flow progress.

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
15. `T-024` `Chandra` fallback adapter tests passed on hard-sample payload and callable fallback path checks in worker integration; full backend suite (`53` tests) passed on `2026-02-15`.
16. `T-106` env/docs contract updates passed full backend suite (`53` tests) on `2026-02-15`.
17. `T-107` fallback endpoint selection tests passed (model-to-endpoint routing and client-selection failure path) and full backend suite (`56` tests) on `2026-02-15`.
18. `T-108` provisioning runbook/docs updates passed full backend suite (`56` tests) on `2026-02-15`.
19. `T-109` inference smoke validation script/tests passed (primary + fallback endpoint checks with evidence JSON) and full backend suite (`58` tests) on `2026-02-15`.
20. `T-025` fallback routing rules passed (confidence/layout triggers + fallback adapter execution path) and full backend suite (`60` tests) on `2026-02-15`.
21. `T-026` normalization tests and worker integration path passed with full backend suite (`63` tests) on `2026-02-15`.
22. `T-027` field confidence map tests and worker persistence path passed with full backend suite (`65` tests) on `2026-02-15`.
23. `T-028` validation-rule tests and queue review-flag escalation passed with full backend suite (`70` tests) on `2026-02-15`.
24. `T-029` extraction persistence assertions passed for schema version/review flag synchronization with full backend suite (`70` tests) on `2026-02-15`.
25. `T-030` job status endpoint tests (success/failed/not-found) passed with full backend suite (`73` tests) on `2026-02-15`.
26. `T-031` extraction endpoint tests (success/document-not-found/extraction-not-found) passed with full backend suite (`76` tests) on `2026-02-15`.
27. `T-032` correction endpoint tests (success/not-found/invalid-path validation + audit persistence checks) passed with full backend suite (`80` tests) on `2026-02-15`.
28. `T-033` JSON export service tests (canonical output + invalid payload rejection) passed with full backend suite (`82` tests) on `2026-02-15`.
29. `T-034` CSV export service tests (deterministic headers/values + invalid payload rejection) passed with full backend suite (`84` tests) on `2026-02-15`.
30. `T-035` XLSX export service tests (Excel workbook opens, numeric/date fields preserved, invalid payload rejection) passed with full backend suite (`86` tests) on `2026-02-15`.
31. `T-036` export endpoint tests (json/xlsx artifact persistence, invalid format, not-found paths) passed with full backend suite (`91` tests) on `2026-02-15`.
32. `T-037` frontend shell checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`; `next build` failed in this sandbox with `spawn EPERM` worker-process limitation.
33. `T-038` upload UX checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, with smoke assertions for single + batch controls and per-file status display.
34. `T-039` document-list checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, including smoke assertions for status/date/vendor filter controls.
35. `T-040` review-page checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, including smoke assertions for side-by-side panel layout and extraction-loading wiring.
36. `T-041` inline-edit checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, including smoke assertions for patch submission wiring and inline edit controls.
37. `T-042` confidence/review-indicator checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, including smoke assertions for threshold/filter controls and confidence-highlight wiring.
38. `T-043` export-action checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, including smoke assertions for JSON/CSV/XLSX action wiring and export request integration.
39. `T-044` UX validation/error checks passed (`typecheck`, `lint`, `test`) on `2026-02-15`, including smoke assertions for hint text, upload error-banner state, and review alert-banner rendering.
40. `T-045` end-to-end smoke checks passed on `2026-02-15`: new `backend/tests/test_e2e_smoke_upload_review_export.py` passed, and full backend suite passed (`92` tests).
41. `T-046` dataset curation checks passed on `2026-02-15`: generator produced manifest and sample corpus, `backend/tests/test_benchmark_dataset.py` passed, and full backend suite passed (`93` tests).
42. `T-047` evaluator checks passed on `2026-02-15`: `backend/tests/test_quality_eval.py` and `backend/tests/test_benchmark_dataset.py` passed, CLI smoke run produced `.local-sandbox/quality-eval.json`, and full backend suite passed (`95` tests).
43. `T-048` quality-gate checks passed on `2026-02-15`: `backend/tests/test_quality_eval.py` and `backend/tests/test_quality_gate.py` passed, evaluator + threshold gate CLI run passed against `datasets/benchmark/v1/ci_predictions.json`, and full backend suite passed (`98` tests).
44. `T-049` queue-retry/dead-letter checks passed on `2026-02-15`: `backend/tests/test_queueing.py` passed with retry/dead-letter scenarios, and full backend suite passed (`100` tests).
45. `T-050` RBAC checks passed on `2026-02-15`: new `backend/tests/test_authorization.py` passed for `admin`/`editor`/`viewer` access controls, and full backend suite passed (`105` tests).
46. `T-051` retention checks passed on `2026-02-15`: new migration `20260215_0005` applied in test runs, `backend/tests/test_retention_cleanup.py` passed for hard-delete + audit logging, and full backend suite passed (`107` tests).
47. `T-052` logging/correlation checks passed on `2026-02-15`: request-id response-header coverage updated in `backend/tests/test_health_endpoints.py`, structured logging sink/unit coverage added in `backend/tests/test_logging_sink.py`, and full backend suite passed (`109` tests).
48. `T-053` metrics instrumentation checks passed on `2026-02-15`: new metrics endpoint/counter tests in `backend/tests/test_metrics.py` passed, queueing instrumentation remained green in `backend/tests/test_queueing.py`, and full backend suite passed (`111` tests).
49. `T-054` alert-threshold checks passed on `2026-02-15`: new alert evaluation module (`svandoc_backend.alerts`) and endpoint coverage in `backend/tests/test_alerts.py` passed, and full backend suite passed (`114` tests).
50. `T-055` rate-limit/abuse guardrail checks passed on `2026-02-15`: new middleware + limiter coverage in `backend/tests/test_rate_limit.py` passed, and full backend suite passed (`117` tests).
51. `T-056` audit-log checks passed on `2026-02-15`: new endpoint coverage in `backend/tests/test_audit_endpoint.py` passed; full backend suite passed (`119` tests); frontend `typecheck`, `lint`, and `test` passed with review page audit UI wiring.
52. `T-057` staging-profile checks passed on `2026-02-15`: profile overlay validation script confirmed `.env.<profile>` precedence for `DATABASE_URL` and `REDIS_URL`; repo staging-profile load checks passed with profile-aware env loader.
53. `T-058` storage-switch checks passed on `2026-02-15`: new integration test `backend/tests/test_storage_backend_switch.py` passed for both `local` and `s3` stub modes; full backend suite passed (`120` tests).
54. `T-059` staging dry-run checks passed on `2026-02-15`: `scripts/staging-dry-run.ps1` validated required staged keys, executed Alembic migrations to head (`20260215_0005`) against SQLite dry-run profile (`t059`), and wrote evidence output to `.local/staging-dry-run.json`.
55. `T-060` pilot metrics checks passed on `2026-02-15`: `backend/tests/test_pilot_metrics.py` passed, `backend/scripts/pilot-metrics.ps1` produced `.local-sandbox/pilot-metrics.json` with completion rate `83.33%` and median time-to-value `410` seconds, and the report was captured in `docs/pilot-report-2026-02-15.md`.
56. `T-061` feedback prioritization checks passed on `2026-02-15`: `backend/tests/test_feedback_prioritization.py` passed, `backend/scripts/feedback-prioritize.ps1` generated ranked output at `.local-sandbox/v1_1-hardening-backlog.json`, and v1.1 ranked backlog doc was finalized at `docs/v1.1-hardening-backlog.md`.
57. `T-062` Google Sheets connector checks passed on `2026-02-15`: `backend/tests/test_google_sheets_export.py`, `backend/tests/test_export_endpoint.py`, and `backend/tests/test_core_schema.py` passed; frontend `typecheck` and `test` passed with review export UI updates; migration validation reached `20260215_0006` head against SQLite dry-run database.
58. `T-063` cloud connector checks passed on `2026-02-15`: `backend/tests/test_cloud_connectors.py`, `backend/tests/test_google_sheets_export.py`, `backend/tests/test_export_endpoint.py`, `backend/tests/test_audit_endpoint.py`, and `backend/tests/test_core_schema.py` passed; frontend `typecheck` and `test` passed; migration validation reached `20260215_0007` head against SQLite dry-run database.
59. `T-064` webhook checks passed on `2026-02-15`: `backend/tests/test_webhooks.py`, `backend/tests/test_export_endpoint.py`, `backend/tests/test_queueing.py`, and `backend/tests/test_core_schema.py` passed (36 tests); migration validation reached `20260215_0008` head against SQLite dry-run database and verified `webhook_delivery_logs` indexes.
60. `T-065` Zapier checks passed on `2026-02-15`: `backend/tests/test_zapier_integration.py`, `backend/tests/test_export_endpoint.py`, `backend/tests/test_job_status_endpoint.py`, and `backend/tests/test_extraction_endpoint.py` passed (22 tests); full backend suite passed (`145` tests).
61. `T-066` Make integration checks passed on `2026-02-15`: `backend/tests/test_make_integration.py`, `backend/tests/test_zapier_integration.py`, and `backend/tests/test_export_endpoint.py` passed (18 tests); full backend suite passed (`147` tests).
62. `T-067` QuickBooks checks passed on `2026-02-15`: `backend/tests/test_quickbooks_connector.py`, `backend/tests/test_export_endpoint.py`, and `backend/tests/test_core_schema.py` passed (26 tests); migration validation reached `20260215_0009` head and verified `quickbooks` format constraint; full backend suite passed (`153` tests).

## 11) Update Protocol For Future Sessions

After each completed task:
1. Update `tasks.md` done rows.
2. Update this `MEMORY.md`:
- completed ranges,
- next three tasks,
- any new caveats or workflow changes.
3. Commit and push.
