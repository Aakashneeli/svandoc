# svanDoc MVP Tasks

Last updated: 2026-02-15 (through T-058)

## How to use this file

- `Priority`: `P0` required for MVP launch, `P1` needed for beta hardening, `P2` post-MVP.
- `Depends On`: task IDs that must be completed first.
- `Owner`: placeholder to assign later.
- `Definition of Done`: objective completion criteria.
- Sequencing note: after completing `T-098` to `T-101`, resume core MVP flow at `T-021`; complete `T-106` to `T-109` before `T-025`; before starting `T-025`, bring up both vLLM servers and pass `backend/scripts/inference-smoke.ps1`; execute `T-102` to `T-105` during deployment phase.

## Task Backlog

| ID | Priority | Task | Depends On | Definition of Done | Owner |
|---|---|---|---|---|---|
| T-001 | P0 | [DONE 2026-02-14] Freeze MVP scope to invoice/receipt extraction only | - | Scope doc approved and out-of-scope list captured (`docs/mvp-scope.md`); validation check passed | Codex |
| T-002 | P0 | [DONE 2026-02-14] Define canonical extraction schema (`invoice`, `receipt`) | T-001 | JSON schema files committed with versioning policy (`contracts/schemas/v1/*.schema.json`, `contracts/schemas/README.md`); contract validation passed | Codex |
| T-003 | P0 | [DONE 2026-02-14] Create repository structure for frontend, backend, worker, shared contracts | T-001 | Folder layout created with README per package (`frontend/README.md`, `backend/README.md`, `worker/README.md`, `contracts/README.md`); structure validation passed | Codex |
| T-004 | P0 | [DONE 2026-02-14] Add `.env.example` with all required local variables | T-003 | `.env.example` added with PRD-required keys and startup hints; automated key/format validation passed | Codex |
| T-005 | P0 | [DONE 2026-02-14] Add local setup guide for Node, Python, PostgreSQL-compatible DB, Redis | T-003 | Setup guide added (`docs/local-setup.md`) with clean-machine validation checklist; completeness validation passed | Codex |
| T-006 | P0 | [DONE 2026-02-14] Add scripts for local startup (`api`, `worker`, `frontend`) | T-004 | Added startup scripts (`scripts/start-api.ps1`, `scripts/start-worker.ps1`, `scripts/start-frontend.ps1`) and orchestrator (`scripts/start-local.ps1`, `scripts/stop-local.ps1`); end-to-end startup/shutdown validation passed | Codex |
| T-007 | P0 | [DONE 2026-02-14] Configure backend Python tooling (formatter, linter, tests) | T-003 | Added backend tooling scripts (`backend/scripts/setup-dev.ps1`, `backend/scripts/format.ps1`, `backend/scripts/lint.ps1`, `backend/scripts/test.ps1`) and stdlib tooling (`backend/tools/*`); setup/lint/test flow passes | Codex |
| T-008 | P0 | [DONE 2026-02-14] Configure frontend tooling (TypeScript checks, lint, tests) | T-003 | Added frontend tooling config (`frontend/package.json`, `frontend/tsconfig.json`, `frontend/eslint.config.mjs`) and smoke test; `typecheck`, `lint`, and `test` pass locally | Codex |
| T-009 | P0 | [DONE 2026-02-14] Define API error format and shared response envelope | T-003 | Added shared envelope/error contracts (`contracts/api/*`) with examples and validator script; contract validations pass | Codex |
| T-010 | P0 | [DONE 2026-02-14] Bootstrap FastAPI app with health and readiness endpoints | T-003 | `/health` and `/ready` return expected payloads | Codex |
| T-011 | P0 | [DONE 2026-02-14] Set up PostgreSQL-compatible connection and migration framework | T-010 | Initial migration runs against local PostgreSQL-compatible instance | Codex |
| T-012 | P0 | [DONE 2026-02-14] Implement core tables: `documents`, `jobs`, `extraction_results` | T-011, T-002 | Tables created with constraints and indexes | Codex |
| T-013 | P0 | [DONE 2026-02-14] Implement tables: `user_corrections`, `export_artifacts` | T-012 | Tables created and relations validated | Codex |
| T-014 | P0 | [DONE 2026-02-14] Build document upload endpoint (`POST /api/documents/upload`) | T-010, T-012 | Upload persists metadata and returns IDs | Codex |
| T-015 | P0 | [DONE 2026-02-14] Implement file validation (type, size, page count) | T-014 | Invalid files rejected with structured errors | Codex |
| T-016 | P0 | [DONE 2026-02-14] Implement storage abstraction interface (`local`, `s3`) | T-014 | Same API works with local backend; S3 stub present | Codex |
| T-017 | P0 | [DONE 2026-02-14] Add checksum generation and duplicate detection | T-014 | Duplicate behavior defined and covered by tests | Codex |
| T-018 | P0 | [DONE 2026-02-14] Integrate Redis and Celery queue | T-010 | Jobs can be enqueued and consumed locally | Codex |
| T-019 | P0 | [DONE 2026-02-14] Create job lifecycle state machine and transitions | T-018, T-012 | Valid transitions enforced in code and DB | Codex |
| T-020 | P0 | [DONE 2026-02-14] Implement worker skeleton with structured logging context | T-018 | Worker logs include `request_id`, `job_id`, `document_id` | Codex |
| T-021 | P0 | [DONE 2026-02-15] Implement image preprocessing (deskew, denoise, orientation) | T-020 | Preprocessing runs on sample corpus with expected output | Codex |
| T-022 | P0 | [DONE 2026-02-15] Build vLLM client module with timeout/retry policies | T-020 | Client handles transient failures and metrics hooks | Codex |
| T-023 | P0 | [DONE 2026-02-15] Integrate `dots.ocr` extraction adapter | T-022 | End-to-end extraction works for baseline samples | Codex |
| T-024 | P0 | [DONE 2026-02-15] Integrate `Chandra` fallback extraction adapter | T-022 | Fallback path callable and tested on hard samples | Codex |
| T-106 | P0 | [DONE 2026-02-15] Pin canonical OCR model IDs and environment contract for dual-endpoint inference | T-022, T-024 | `docs/local-setup.md` and `.env.example` define canonical IDs (`rednote-hilab/dots.ocr`, `datalab-to/chandra`) and endpoint vars (`VLLM_BASE_URL`, `VLLM_FALLBACK_BASE_URL`) with clear defaults/notes | Codex |
| T-107 | P0 | [DONE 2026-02-15] Implement backend support for fallback inference endpoint selection | T-106, T-022, T-024 | Runtime selects primary vs fallback base URL by model path; fallback client path covered by unit tests and structured failure handling | Codex |
| T-108 | P0 | [DONE 2026-02-15] Add local model provisioning runbook for Hugging Face + dual vLLM servers | T-106, T-107 | Runbook includes HF auth, model pull/serve commands, GPU/VRAM guidance, cache paths, and troubleshooting for both models | Codex |
| T-109 | P0 | [DONE 2026-02-15] Add inference smoke validation for `dots.ocr` and `chandra` endpoints | T-107, T-108 | Validation script/checklist confirms both endpoints reachable and one successful inference call per model with evidence output | Codex |
| T-025 | P0 | [DONE 2026-02-15] Implement routing rules from `dots.ocr` to fallback | T-023, T-024, T-109 | Routing triggers based on confidence/layout thresholds | Codex |
| T-026 | P0 | [DONE 2026-02-15] Normalize raw OCR output into canonical schema | T-023, T-024, T-002 | Normalization handles required schema fields | Codex |
| T-027 | P0 | [DONE 2026-02-15] Implement field-level confidence scoring map | T-026 | Confidence values emitted for all extractable fields | Codex |
| T-028 | P0 | [DONE 2026-02-15] Add validation rules (total math, date formats, currency consistency) | T-026 | Invalid fields flagged with actionable messages | Codex |
| T-029 | P0 | [DONE 2026-02-15] Persist extraction results and review flags | T-026, T-027, T-028 | DB row saved with schema version and status flags | Codex |
| T-030 | P0 | [DONE 2026-02-15] Implement `GET /api/jobs/{job_id}` endpoint | T-019 | Endpoint returns current status and error details | Codex |
| T-031 | P0 | [DONE 2026-02-15] Implement `GET /api/documents/{id}/extraction` endpoint | T-029 | Endpoint returns extraction payload and confidence map | Codex |
| T-032 | P0 | [DONE 2026-02-15] Implement correction endpoint (`PATCH /extraction`) | T-031, T-013 | Corrections persist with actor and timestamp | Codex |
| T-033 | P0 | [DONE 2026-02-15] Implement export service for `JSON` | T-031 | JSON export output matches canonical schema | Codex |
| T-034 | P0 | [DONE 2026-02-15] Implement export service for `CSV` | T-033 | CSV headers and values are deterministic and tested | Codex |
| T-035 | P0 | [DONE 2026-02-15] Implement export service for `XLSX` | T-033 | XLSX opens in Excel and preserves numeric/date fields | Codex |
| T-036 | P0 | [DONE 2026-02-15] Implement export endpoint (`POST /api/documents/{id}/export`) | T-034, T-035, T-013 | Export artifact metadata is persisted and downloadable | Codex |
| T-037 | P0 | [DONE 2026-02-15] Bootstrap Next.js app shell with auth-ready layout | T-003 | Base routes and navigation load successfully | Codex |
| T-038 | P0 | [DONE 2026-02-15] Build upload page with single and batch upload UX | T-037, T-014 | Users can upload multiple files and see per-file status | Codex |
| T-039 | P0 | [DONE 2026-02-15] Build document list page with status and search filters | T-037, T-030 | Documents searchable by status/date/vendor metadata | Codex |
| T-040 | P0 | [DONE 2026-02-15] Build review page side-by-side document and extracted data | T-039, T-031 | Review page loads document + extracted payload correctly | Codex |
| T-041 | P0 | [DONE 2026-02-15] Implement inline edit UI and correction submission | T-040, T-032 | Edited fields save and reflect in UI state | Codex |
| T-042 | P0 | [DONE 2026-02-15] Implement confidence highlight and review-required indicators | T-040, T-027 | Low-confidence fields clearly visible and filterable | Codex |
| T-043 | P0 | [DONE 2026-02-15] Implement export UI actions for JSON/CSV/XLSX | T-040, T-036 | Users can trigger and download all MVP formats | Codex |
| T-044 | P0 | [DONE 2026-02-15] Add frontend validation hints and error banners | T-038, T-040 | API and validation errors are understandable for users | Codex |
| T-045 | P0 | [DONE 2026-02-15] Build end-to-end smoke test: upload -> review -> export | T-043 | Automated smoke test passes on local stack | Codex |
| T-046 | P0 | [DONE 2026-02-15] Curate benchmark dataset (invoice + receipt variants) | T-001 | Dataset includes clean/noisy/rotated/multi-layout samples | Codex |
| T-047 | P0 | [DONE 2026-02-15] Implement extraction quality evaluation script | T-046, T-026 | Script outputs precision/recall by field and document type | Codex |
| T-048 | P0 | [DONE 2026-02-15] Add regression thresholds for extraction quality in CI | T-047 | CI fails when quality drops below agreed thresholds | Codex |
| T-049 | P0 | [DONE 2026-02-15] Add integration tests for queue retries and failure states | T-019, T-020 | Retry and dead-letter behavior verified by tests | Codex |
| T-050 | P1 | [DONE 2026-02-15] Add role-based authorization checks (Admin/Editor/Viewer) | T-012 | Protected endpoints enforce role checks with tests | Codex |
| T-051 | P1 | [DONE 2026-02-15] Add document retention policy and hard-delete job | T-012 | Retention rules configurable and deletions auditable | Codex |
| T-052 | P1 | [DONE 2026-02-15] Add structured logging sink and request correlation IDs | T-020 | Logs queryable by request and job IDs | Codex |
| T-053 | P1 | [DONE 2026-02-15] Add metrics instrumentation (latency, queue depth, error rate) | T-020 | Metrics exposed and sampled in local dashboard | Codex |
| T-054 | P1 | [DONE 2026-02-15] Define alert thresholds for repeated failures and backlog | T-053 | Alert rules documented and test-triggered once | Codex |
| T-055 | P1 | [DONE 2026-02-15] Add API rate limiting and abuse guardrails | T-010 | Rate limits active and tested | Codex |
| T-056 | P1 | [DONE 2026-02-15] Add audit log views for correction and export events | T-013, T-041, T-036 | Users can inspect historical edits and exports | Codex |
| T-057 | P1 | [DONE 2026-02-15] Create staging config profile for managed Supabase Postgres and Redis | T-004 | Environment swap works without code changes | Codex |
| T-058 | P1 | [DONE 2026-02-15] Implement storage backend switch test (`local` -> `s3`) | T-016 | Same upload/export tests pass under both backends | Codex |
| T-059 | P1 | Create local-to-cloud migration runbook | T-057, T-058 | Runbook validated in staging dry run | Unassigned |
| T-060 | P1 | Run pilot with 5 to 10 target users and collect workflow metrics | T-045 | Pilot report includes completion and time-to-value metrics | Unassigned |
| T-061 | P1 | Prioritize beta feedback and create v1.1 hardening backlog | T-060 | Ranked backlog with impact/effort and owners | Unassigned |
| T-062 | P2 | Implement Google Sheets direct export connector | T-036 | Users can push extraction results to a selected Sheet via OAuth flow | Unassigned |
| T-063 | P2 | Implement cloud storage connectors (Google Drive, OneDrive, Dropbox) | T-036 | Export artifacts can be saved to each provider with status tracking | Unassigned |
| T-064 | P2 | Implement outbound webhook events (`job.completed`, `job.failed`, `export.created`) | T-030, T-036 | Signed webhooks delivered with retries and delivery logs | Unassigned |
| T-065 | P2 | Build Zapier integration using webhook/API triggers and actions | T-064 | Zapier app supports trigger on completion and action to fetch results | Unassigned |
| T-066 | P2 | Build Make.com integration templates and connection guide | T-064 | Make templates run end-to-end for upload and export workflows | Unassigned |
| T-067 | P2 | Implement QuickBooks Online connector for invoice/receipt payload sync | T-061, T-002 | Validated mapping for vendors, amounts, taxes, and references | Unassigned |
| T-068 | P2 | Implement Xero connector with sync status and retry handling | T-067 | Xero sync works with idempotent retries and reconciliation logs | Unassigned |
| T-069 | P2 | Implement phased Sage/Tally connector strategy | T-061, T-036 | Sage integration path and Tally import package delivered with docs | Unassigned |
| T-070 | P2 | Implement email intake with workspace-specific ingestion address | T-014, T-018 | Forwarded emails create document jobs with parsing safeguards | Unassigned |
| T-071 | P2 | Launch public REST API with API keys and scoped permissions | T-055, T-030, T-031, T-036 | External clients can securely access document/job/extraction/export endpoints | Unassigned |
| T-072 | P2 | Publish developer docs and starter SDKs (TypeScript and Python) | T-071 | Quickstart apps for both SDKs run against staging API | Unassigned |
| T-073 | P2 | Implement custom extraction templates (schema builder + field mapping UI) | T-026, T-041 | Users can define and apply templates to recurring document formats | Unassigned |
| T-074 | P2 | Implement template learning from user corrections (opt-in) | T-073, T-041 | Repeated corrections improve extraction suggestions for matching layouts | Unassigned |
| T-075 | P2 | Implement advanced table extraction (multi-page stitching, merged cells) | T-024, T-026 | Complex table benchmark accuracy improves and passes regression gates | Unassigned |
| T-076 | P2 | Add handwriting-focused extraction route and quality benchmark | T-024, T-046 | Handwriting test corpus tracked with explicit acceptance metrics | Unassigned |
| T-077 | P2 | Expand multilingual support with automatic language detection | T-023, T-024 | Additional language pack support validated on multilingual dataset | Unassigned |
| T-078 | P2 | Implement immutable audit trail and exportable audit reports | T-056 | Every extraction edit/export event is queryable and exportable | Unassigned |
| T-079 | P2 | Implement approval workflow (`Reviewer` -> `Approver`) | T-041, T-078 | Documents can require approval before final export | Unassigned |
| T-080 | P3 | Add enterprise SSO/SAML and SCIM provisioning | T-050 | Enterprise identity flows and provisioning tests pass | Unassigned |
| T-081 | P3 | Implement SOC2 readiness controls and evidence collection workflows | T-052, T-053, T-078 | Control matrix, evidence jobs, and incident playbook are documented and operational | Unassigned |
| T-082 | P3 | Implement data residency controls (US/EU storage and processing) | T-016, T-057 | Workspace-level region assignment enforced end-to-end | Unassigned |
| T-083 | P3 | Build self-hosted/on-prem deployment package (Docker/K8s) | T-059 | Reference deployment runs with documented install and upgrade path | Unassigned |
| T-084 | P3 | Implement usage metering and billing foundation (deferred) | T-061 | Metering events and plan limits available behind feature flag | Unassigned |
| T-085 | P1 | Define constrained instruction contract for extraction/output prompts (`include`, `exclude`, `rename`, `format`) | T-026, T-031 | Contract spec and validator implemented; invalid/ambiguous directives return structured errors | Unassigned |
| T-086 | P1 | Add DB models and migration for workspace instruction profiles and template profiles | T-013, T-050 | Tables, relations, indexes, and migration tests added for reusable workspace profiles | Unassigned |
| T-087 | P1 | Implement template upload endpoint (`POST /api/templates/upload`) for `xlsx`/`csv` | T-086 | Template files stored with metadata/version; file validation and error envelopes covered by tests | Unassigned |
| T-088 | P1 | Implement template mapping endpoints for canonical field to cell/column binding | T-087, T-031 | CRUD mapping APIs persist strict bindings and validate required target locations | Unassigned |
| T-089 | P1 | Extend export endpoint to accept `template_id`, `instruction_profile_id`, and inline prompt directives | T-036, T-085, T-088 | Export request supports template and instruction options with deterministic validation and response schema | Unassigned |
| T-090 | P1 | Implement strict template fill engine for mapped exports | T-089 | Exported file fills mapped cells/columns exactly; unmapped required fields fail with actionable errors | Unassigned |
| T-091 | P1 | Implement fallback export policy when no template is provided (default svanDoc export path) | T-089, T-035 | No-template exports continue to produce default JSON/CSV/XLSX outputs unchanged | Unassigned |
| T-092 | P1 | Add frontend template upload/manage section and export instruction UI (prompt + profile picker) | T-043, T-087, T-089 | Users can upload/select template, add constrained prompt directives, and run export from UI | Unassigned |
| T-093 | P1 | Add end-to-end tests for template and non-template paths with prompt directives | T-092, T-045 | E2E covers template fill success, strict mapping failure, skip/include directives, and no-template fallback | Unassigned |
| T-094 | P2 | Add hybrid prompt normalizer (semi-free-form text to constrained directives) with safe rejection | T-085, T-093 | Lightweight parser maps supported phrases to directives; unsupported intent rejected explicitly | Unassigned |
| T-095 | P2 | Add template versioning, workspace default template selection, and change history | T-087, T-056 | Versioned template lifecycle with default selection and auditable change records | Unassigned |
| T-096 | P2 | Add output preset packs for external tools using CSV/XLSX/JSON shaping profiles | T-089 | Presets generate tool-friendly headers/structures without requiring direct connector auth | Unassigned |
| T-097 | P2 | Integrate export template mappings with custom extraction templates | T-073, T-095 | Extraction template outputs can be bound to export templates with compatibility checks | Unassigned |
| T-098 | P0 | [DONE 2026-02-15] Configure backend database runtime for Supabase Postgres (`DATABASE_URL`, SSL, pooling-safe defaults) | T-020 | API boots with Supabase connection string; DB session/engine tests pass with Supabase-style URL inputs | Codex |
| T-099 | P0 | [DONE 2026-02-15] Update environment/docs for Supabase-first development and migration workflow | T-098 | `.env.example`, `docs/local-setup.md`, and backend README document Supabase setup, secrets handling, and migration commands | Codex |
| T-100 | P0 | [DONE 2026-02-15] Validate Alembic migrations end-to-end against Supabase Postgres | T-099 | `alembic upgrade head` and `alembic current` validated on Supabase; migration notes captured | Codex |
| T-101 | P0 | [DONE 2026-02-15] Strengthen readiness checks to include DB and Redis dependency health | T-099, T-018 | `/ready` reports dependency status and fails when critical dependencies are unavailable; tests added | Codex |
| T-102 | P0 | Configure production CORS and API base URL wiring for Vercel frontend -> hosted FastAPI | T-101, T-037 | Frontend can target hosted API URL; backend CORS allows configured Vercel origin(s) only | Unassigned |
| T-103 | P0 | Define and document split deployment topology (Vercel frontend + hosted API/worker + managed Redis) | T-102 | Deployment runbook includes env vars, service responsibilities, start commands, and rollback notes | Unassigned |
| T-104 | P0 | Add deploy gate for migration-before-release and hosted smoke validation | T-103 | Deployment checklist/automation enforces migrations before API rollout and validates upload -> queue -> completion smoke path | Unassigned |
| T-105 | P0 | Run first managed-environment smoke test with Vercel frontend and Supabase-backed API | T-104 | End-to-end flow verified in hosted setup with evidence logged and follow-up issues captured | Unassigned |

## Milestone Mapping (MVP + Post-MVP)

| Milestone | Required Tasks |
|---|---|
| M1 Local Foundation | T-001 to T-020 |
| M2 Extraction Pipeline | T-021 to T-031 |
| M3 Review and Export | T-032 to T-045 |
| M4 Quality Baseline | T-046 to T-049 |
| M5 Beta Hardening | T-050 to T-061 |
| M6 Connector Expansion | T-062 to T-070 |
| M7 API and Intelligence Expansion | T-071 to T-077 |
| M8 Enterprise Readiness | T-078 to T-083 |
| M9 Commercialization (Deferred) | T-084 |
| M10 Guided Template Export | T-085 to T-093 |
| M11 Advanced Personalization | T-094 to T-097 |
| M12 Managed Deploy Foundation | T-098 to T-105 |
| M13 Inference Provisioning | T-106 to T-109 |

## MVP Exit Checklist

| Check | Pass Criteria |
|---|---|
| Accuracy | Invoice >= 92 percent and receipt >= 88 percent on benchmark set |
| Performance | P95 processing latency < 12 seconds per page |
| Reliability | Retry logic and failure handling pass integration tests |
| Usability | Pilot users complete upload -> review -> export with >= 80 percent success |
| Security | Role checks and retention/delete workflows validated |

