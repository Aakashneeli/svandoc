# svanDoc Memory File

Last updated: 2026-02-25 (`T-111` completed; `T-112` is next; housekeeping fixes applied)
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
4. RunPod cloud-GPU inference as default, with optional local inference for development fallback only.

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
- Inference: RunPod Serverless vLLM-compatible endpoints, primary `dots.ocr`, fallback `chandra` (fail-closed policy; no automatic local GPU fallback in outages).

## 4) Environment Notes

Primary env template is `.env.example`.

Important runtime notes for this machine/session:
1. Use `npm.cmd` (not `npm`) due PowerShell script policy behavior.
2. Frontend install/check commands should set local npm cache dirs if permission issues appear.
3. Create and use repo venv `myvenv` before backend package installs.
4. Backend scripts auto-prefer `myvenv\Scripts\python.exe` when present on Windows; non-Windows runtime falls back to `python`.
5. Readiness now checks both DB and Redis; `/ready` returns `503 DEPENDENCY_UNAVAILABLE` on dependency failures.
6. `python-multipart` is required for upload endpoint form parsing and is now pinned in backend dependencies.
7. Use `uv` for Python dependency management (`uv pip install -r <requirements-file>`); set `UV_CACHE_DIR` under repo-local paths if default cache permissions fail.
8. Supabase hostnames (`*.supabase.co`) get `sslmode=require` automatically if not provided in `DATABASE_URL`.
9. Use Supabase pooler/IPv4-capable `DATABASE_URL` for this environment; direct DB host may fail due to IPv6-only resolution.
10. `T-106` to `T-109` are completed historical local-inference provisioning tasks; RunPod migration tasks `T-110` to `T-115` now gate upcoming extraction/deployment work.
11. Canonical model IDs remain `rednote-hilab/dots.ocr` (primary) and `datalab-to/chandra` (fallback), with dual endpoint contract `VLLM_BASE_URL` and `VLLM_FALLBACK_BASE_URL` now targeting RunPod by default.
12. Outbound webhook delivery is controlled by `WEBHOOK_ENDPOINTS`, `WEBHOOK_SIGNING_SECRET`, and retry vars (`WEBHOOK_MAX_ATTEMPTS`, `WEBHOOK_TIMEOUT_SECONDS`, `WEBHOOK_RETRY_BACKOFF_SECONDS`).
13. Current Linux sandbox runtime uses Python `3.12`; FastAPI `TestClient`-based unit tests can hang in this environment (observed in `anyio/from_thread` path). `backend/scripts/test.ps1` now defaults to a per-module timeout runner to prevent indefinite hangs; use Python `3.11` for the most stable full-suite execution.
14. Inference outage policy is fail-closed for hosted GPU paths: retries + dead-letter handling apply; no automatic personal/local GPU failover in production flows.
15. RunPod-first env contract now includes `RUNPOD_ENDPOINT_ID_PRIMARY` / `RUNPOD_ENDPOINT_ID_FALLBACK` and `VLLM_API_KEY` secret-handling guidance; localhost vLLM URLs are documented as development-only fallback overrides.
16. Inference smoke evidence now emits deterministic `result_code` and `failure_codes`, with explicit per-target failure codes for endpoint configuration, `/models` reachability/model-availability, and completion checks.
17. If Git shows mass modified files on WSL/mounted filesystems due executable-bit flips, set repository config `git config core.filemode false` to suppress file-mode noise and keep status focused on real content changes.

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
59. `T-068`: Xero connector added for export sync (`format=xero`) with idempotent retry handling (`Idempotency-Key`), per-attempt reconciliation logging in `xero_sync_logs`, migration `20260215_0010`, and runbook (`docs/xero-connector.md`).
60. `T-069`: Phased Sage/Tally connector strategy implemented with export endpoint support (`format=sage|tally`), Sage phase-plan artifact generation, Tally import package generation (`manifest.json`, `voucher.xml`, `summary.csv`), migration `20260216_0011`, and runbook (`docs/sage-tally-connectors.md`).
61. `T-070`: Email intake flow added at `POST /api/documents/email-intake` with workspace-specific ingestion address validation, RFC822 attachment parsing, sender-domain allow-list + attachment-count safeguards, upload validation/dedup reuse, and runbook/env contract updates (`docs/email-intake.md`, `.env.example`).
62. `T-071`: Public REST API launched with API-key and scope enforcement (`PUBLIC_API_KEYS_JSON`) via new `/api/public/*` endpoints for upload, job status, extraction fetch, and export; auth helper module added (`svandoc_backend.api_keys`) with explicit `401`/`403` behavior and runbook (`docs/public-api.md`).
63. `T-072`: Developer SDK package starters published for Python and TypeScript (`sdk/python`, `sdk/typescript`) with runnable quickstart apps, shared public API workflow methods (upload -> job -> extraction -> export), and developer runbook documentation (`docs/developer-sdks.md`).
64. `T-073`: Custom extraction templates implemented with workspace-scoped template persistence (`extraction_templates` table + migration `20260216_0012`), template create/list/apply endpoints (`/api/templates`, `/api/documents/{id}/templates/apply`), mapped output persistence under `structured_payload.template_output`, and review-page schema/mapping UI to create/apply templates.
65. `T-074`: Template learning (opt-in) implemented with persisted learning rules (`template_learning_rules` table + migration `20260216_0013`), correction-event aggregation keyed by team/template/field/value, request-level opt-in control (`x-template-learning-opt-in`), and learned suggestion emission during template apply (`template_output.learned_suggestions`) for repeated corrections.
66. `T-075`: Advanced table extraction implemented with multi-page table stitching and merged-cell expansion (`svandoc_backend.table_extraction`), integrated into normalization to prefer table-derived line items when available, and benchmark regression gate coverage added for complex table scenarios.
67. `T-110`: RunPod-first inference env/secrets contract aligned across `.env.example`, `.env.staging.example`, and setup/migration docs, including explicit `VLLM_API_KEY` handling and development-only local vLLM fallback guidance.
68. `T-111`: Inference smoke validation hardened for RunPod dual endpoints with deterministic evidence output (`result_code`, ordered `failure_codes`) and explicit primary/fallback failure codes for connectivity/model/readiness failures.
22. `T-098` to `T-099`: Supabase-first DB runtime/env/docs updates (URL normalization, SSL defaults, pool settings, setup docs).
23. `T-100`: Alembic migration validation completed against Supabase-managed Postgres.
24. `T-101`: readiness dependency checks for DB + Redis with failure envelopes and tests.

Task status source of truth: `tasks.md`.

## 6) Next Tasks To Execute

Next in strict order:
1. `T-112` Harden inference client policy for RunPod serverless behavior (fail-closed). `NEXT`
2. `T-113` Update cloud deployment/inference runbook for RunPod operations.
3. `T-114` Add deploy gate for RunPod inference readiness.
4. `T-115` Execute managed-environment smoke with RunPod-backed inference.
5. `T-076` Add handwriting-focused extraction route and quality benchmark.
6. `T-077` Expand multilingual support with automatic language detection.
7. `T-078` Implement immutable audit trail and exportable audit reports.
8. Deployment tasks `T-102` to `T-105` execute after `T-115` is complete.

Completed snapshot for `T-111` (2026-02-22):
1. Hardened `svandoc_backend.inference_smoke` to return deterministic top-level `result_code`/`failure_codes` and per-target `status`/`failure_codes`.
2. Added explicit failure-code taxonomy for both primary and fallback checks: endpoint configuration, `/models` reachability, target-model availability, and completion-call readiness.
3. Added fast-fail handling for placeholder/unconfigured endpoint URLs to avoid ambiguous network errors.
4. Expanded smoke tests in `backend/tests/test_inference_smoke.py` to cover success, completion failure, model-missing failure, and unconfigured-endpoint failure behavior.
5. Verified CLI evidence behavior using placeholder RunPod URLs (`PRIMARY_ENDPOINT_UNCONFIGURED` / `FALLBACK_ENDPOINT_UNCONFIGURED`).

Completed snapshot for `T-110` (2026-02-22):
1. Updated RunPod-first OCR env contract in `.env.example` and `.env.staging.example` with endpoint URL format, API key secret handling, and optional endpoint IDs.
2. Updated setup/migration docs to require RunPod env vars for default inference and document local vLLM as development-only fallback.
3. Updated backend inference notes to reflect RunPod-first runtime policy and secret handling expectations.
4. Targeted regression tests passed:
   - `backend/tests/test_vllm_client.py`
   - `backend/tests/test_inference_smoke.py`
   - `backend/tests/test_queueing.py`

Completed snapshot for `T-075` (2026-02-22):
1. Implemented advanced table extraction helper module at `backend/src/svandoc_backend/table_extraction.py` with multi-page stitching and merged-cell expansion.
2. Integrated advanced table parsing into normalization path in `backend/src/svandoc_backend/normalization.py` (prefers advanced table-derived line items when available).
3. Added new tests/datasets:
   - `backend/tests/test_table_extraction.py`
   - `backend/tests/test_table_quality_benchmark.py`
   - `datasets/benchmark/v1/table_ground_truth.json`
   - `datasets/benchmark/v1/table_ci_predictions.json`
4. Targeted tests passed:
   - `backend/tests/test_table_extraction.py`
   - `backend/tests/test_normalization.py`
   - `backend/tests/test_table_quality_benchmark.py`
   - `backend/tests/test_quality_eval.py`
   - `backend/tests/test_quality_gate.py`
   - `backend/tests/test_queueing.py`
5. Task marked complete in `tasks.md` based on DoD satisfaction (complex table benchmark coverage and regression gate pass on targeted suite).
6. Cross-cutting environment caveat remains: full backend `unittest discover` run still hangs in this Python `3.12` sandbox when `TestClient`-based tests execute.

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
63. `T-068` Xero checks passed on `2026-02-15`: `backend/tests/test_xero_connector.py`, `backend/tests/test_export_endpoint.py`, and `backend/tests/test_core_schema.py` passed (30 tests); migration validation reached `20260215_0010` head and verified `xero_sync_logs` indexes + export-format constraint; full backend suite passed (`160` tests).
64. `T-069` Sage/Tally checks passed on `2026-02-16`: `backend/tests/test_sage_connector.py`, `backend/tests/test_tally_connector.py`, `backend/tests/test_export_endpoint.py`, and `backend/tests/test_core_schema.py` passed (`31` tests via `unittest`); Alembic migration validation reached `20260216_0011` head and verified updated export-format constraint includes `sage` and `tally`.
65. `T-070` email-intake checks passed on `2026-02-16`: `backend/tests/test_email_intake.py`, `backend/tests/test_upload_endpoint.py`, and `backend/tests/test_export_endpoint.py` passed (`34` tests via `unittest`) validating workspace address checks, sender-domain guardrails, attachment-limit safeguards, and end-to-end document/job creation from forwarded `.eml` attachments.
66. `T-071` public API checks passed on `2026-02-16`: `backend/tests/test_public_api.py`, `backend/tests/test_upload_endpoint.py`, `backend/tests/test_job_status_endpoint.py`, `backend/tests/test_extraction_endpoint.py`, and `backend/tests/test_export_endpoint.py` passed (`40` tests via `unittest`) validating API-key auth, scoped permission enforcement, and external upload -> job -> extraction -> export flows.
67. `T-072` SDK quickstart checks passed on `2026-02-16`: `backend/tests/test_sdk_quickstarts.py` and `backend/tests/test_public_api.py` passed (`6` tests via `unittest`), including execution of both `sdk/python/examples/quickstart.py` and `sdk/typescript/examples/quickstart.mjs` against a mock public API host.
68. `T-073` extraction-template checks passed on `2026-02-16`: `backend/tests/test_extraction_templates.py`, `backend/tests/test_core_schema.py`, and `backend/tests/test_extraction_endpoint.py` passed (`16` tests via `unittest`); migration validation reached `20260216_0012` head; frontend `typecheck`, `lint`, and `test` passed with new review-page template create/apply UI.
69. `T-074` template-learning checks passed on `2026-02-16`: `backend/tests/test_template_learning.py`, `backend/tests/test_extraction_templates.py`, and `backend/tests/test_core_schema.py` passed (`16` tests via `unittest`); migration validation reached `20260216_0013` head and confirmed learning-rule table/indexes; frontend smoke tests remained green.
70. `T-075` advanced-table checks passed on `2026-02-22`: `backend/tests/test_table_extraction.py`, `backend/tests/test_normalization.py`, `backend/tests/test_table_quality_benchmark.py`, `backend/tests/test_quality_eval.py`, `backend/tests/test_quality_gate.py`, and `backend/tests/test_queueing.py` passed (`26` tests via `unittest`); raw `unittest discover` in this Python `3.12` sandbox can still hang on `TestClient` paths, so backend test script now defaults to module-level timeout execution.
71. RunPod migration validation target (planned): `T-112` must verify fail-closed inference outage handling (retry/dead-letter, no auto local fallback) under hosted RunPod endpoint behavior.
72. `T-110` contract alignment checks passed on `2026-02-22`: `.env.example`, `.env.staging.example`, `docs/local-setup.md`, `docs/local-to-cloud-migration-runbook.md`, `docs/inference-model-setup.md`, and `backend/README.md` were updated for RunPod-first endpoint/auth guidance; targeted backend regression tests passed (`backend/tests/test_vllm_client.py`, `backend/tests/test_inference_smoke.py`, `backend/tests/test_queueing.py`; `21` tests via `unittest`).
73. `T-111` smoke-hardening checks passed on `2026-02-22`: `backend/tests/test_inference_smoke.py`, `backend/tests/test_vllm_client.py`, and `backend/tests/test_queueing.py` passed (`23` tests via `unittest`); CLI smoke execution with placeholder RunPod URLs produced deterministic evidence (`result_code=PRIMARY_ENDPOINT_UNCONFIGURED`) at `backend/.local-sandbox/inference-smoke-t111.json`.
74. Housekeeping fixes on `2026-02-25`: restored `datasets/benchmark/v1/table_ground_truth.json` and `datasets/benchmark/v1/table_ci_predictions.json` so `backend/tests/test_table_quality_benchmark.py` fixtures are present; resolved mass git-status file-mode noise in WSL environments via repository `core.filemode=false` guidance.

## 11) Update Protocol For Future Sessions

After each completed task:
1. Update `tasks.md` done rows.
2. Update this `MEMORY.md`:
- completed ranges,
- next three tasks,
- any new caveats or workflow changes.
3. Commit and push.
