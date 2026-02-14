# svanDoc MVP Tasks

Last updated: 2026-02-14

## How to use this file

- `Priority`: `P0` required for MVP launch, `P1` needed for beta hardening, `P2` post-MVP.
- `Depends On`: task IDs that must be completed first.
- `Owner`: placeholder to assign later.
- `Definition of Done`: objective completion criteria.

## Task Backlog

| ID | Priority | Task | Depends On | Definition of Done | Owner |
|---|---|---|---|---|---|
| T-001 | P0 | Freeze MVP scope to invoice/receipt extraction only | - | Scope doc approved and out-of-scope list captured | Unassigned |
| T-002 | P0 | Define canonical extraction schema (`invoice`, `receipt`) | T-001 | JSON schema files committed with versioning policy | Unassigned |
| T-003 | P0 | Create repository structure for frontend, backend, worker, shared contracts | T-001 | Folder layout created with README per package | Unassigned |
| T-004 | P0 | Add `.env.example` with all required local variables | T-003 | `.env.example` exists and startup works with documented values | Unassigned |
| T-005 | P0 | Add local setup guide for Node, Python, Postgres, Redis | T-003 | Setup doc tested on a clean machine checklist | Unassigned |
| T-006 | P0 | Add scripts for local startup (`api`, `worker`, `frontend`) | T-004 | One-command scripts start all services successfully | Unassigned |
| T-007 | P0 | Configure backend Python tooling (formatter, linter, tests) | T-003 | Lint and test commands run cleanly | Unassigned |
| T-008 | P0 | Configure frontend tooling (TypeScript checks, lint, tests) | T-003 | Frontend checks run cleanly in CI/local | Unassigned |
| T-009 | P0 | Define API error format and shared response envelope | T-003 | API responses use one documented structure | Unassigned |
| T-010 | P0 | Bootstrap FastAPI app with health and readiness endpoints | T-003 | `/health` and `/ready` return expected payloads | Unassigned |
| T-011 | P0 | Set up PostgreSQL connection and migration framework | T-010 | Initial migration runs against local Postgres | Unassigned |
| T-012 | P0 | Implement core tables: `documents`, `jobs`, `extraction_results` | T-011, T-002 | Tables created with constraints and indexes | Unassigned |
| T-013 | P0 | Implement tables: `user_corrections`, `export_artifacts` | T-012 | Tables created and relations validated | Unassigned |
| T-014 | P0 | Build document upload endpoint (`POST /api/documents/upload`) | T-010, T-012 | Upload persists metadata and returns IDs | Unassigned |
| T-015 | P0 | Implement file validation (type, size, page count) | T-014 | Invalid files rejected with structured errors | Unassigned |
| T-016 | P0 | Implement storage abstraction interface (`local`, `s3`) | T-014 | Same API works with local backend; S3 stub present | Unassigned |
| T-017 | P0 | Add checksum generation and duplicate detection | T-014 | Duplicate behavior defined and covered by tests | Unassigned |
| T-018 | P0 | Integrate Redis and Celery queue | T-010 | Jobs can be enqueued and consumed locally | Unassigned |
| T-019 | P0 | Create job lifecycle state machine and transitions | T-018, T-012 | Valid transitions enforced in code and DB | Unassigned |
| T-020 | P0 | Implement worker skeleton with structured logging context | T-018 | Worker logs include `request_id`, `job_id`, `document_id` | Unassigned |
| T-021 | P0 | Implement image preprocessing (deskew, denoise, orientation) | T-020 | Preprocessing runs on sample corpus with expected output | Unassigned |
| T-022 | P0 | Build vLLM client module with timeout/retry policies | T-020 | Client handles transient failures and metrics hooks | Unassigned |
| T-023 | P0 | Integrate `dots.ocr` extraction adapter | T-022 | End-to-end extraction works for baseline samples | Unassigned |
| T-024 | P0 | Integrate `Chandra` fallback extraction adapter | T-022 | Fallback path callable and tested on hard samples | Unassigned |
| T-025 | P0 | Implement routing rules from `dots.ocr` to fallback | T-023, T-024 | Routing triggers based on confidence/layout thresholds | Unassigned |
| T-026 | P0 | Normalize raw OCR output into canonical schema | T-023, T-024, T-002 | Normalization handles required schema fields | Unassigned |
| T-027 | P0 | Implement field-level confidence scoring map | T-026 | Confidence values emitted for all extractable fields | Unassigned |
| T-028 | P0 | Add validation rules (total math, date formats, currency consistency) | T-026 | Invalid fields flagged with actionable messages | Unassigned |
| T-029 | P0 | Persist extraction results and review flags | T-026, T-027, T-028 | DB row saved with schema version and status flags | Unassigned |
| T-030 | P0 | Implement `GET /api/jobs/{job_id}` endpoint | T-019 | Endpoint returns current status and error details | Unassigned |
| T-031 | P0 | Implement `GET /api/documents/{id}/extraction` endpoint | T-029 | Endpoint returns extraction payload and confidence map | Unassigned |
| T-032 | P0 | Implement correction endpoint (`PATCH /extraction`) | T-031, T-013 | Corrections persist with actor and timestamp | Unassigned |
| T-033 | P0 | Implement export service for `JSON` | T-031 | JSON export output matches canonical schema | Unassigned |
| T-034 | P0 | Implement export service for `CSV` | T-033 | CSV headers and values are deterministic and tested | Unassigned |
| T-035 | P0 | Implement export service for `XLSX` | T-033 | XLSX opens in Excel and preserves numeric/date fields | Unassigned |
| T-036 | P0 | Implement export endpoint (`POST /api/documents/{id}/export`) | T-034, T-035, T-013 | Export artifact metadata is persisted and downloadable | Unassigned |
| T-037 | P0 | Bootstrap Next.js app shell with auth-ready layout | T-003 | Base routes and navigation load successfully | Unassigned |
| T-038 | P0 | Build upload page with single and batch upload UX | T-037, T-014 | Users can upload multiple files and see per-file status | Unassigned |
| T-039 | P0 | Build document list page with status and search filters | T-037, T-030 | Documents searchable by status/date/vendor metadata | Unassigned |
| T-040 | P0 | Build review page side-by-side document and extracted data | T-039, T-031 | Review page loads document + extracted payload correctly | Unassigned |
| T-041 | P0 | Implement inline edit UI and correction submission | T-040, T-032 | Edited fields save and reflect in UI state | Unassigned |
| T-042 | P0 | Implement confidence highlight and review-required indicators | T-040, T-027 | Low-confidence fields clearly visible and filterable | Unassigned |
| T-043 | P0 | Implement export UI actions for JSON/CSV/XLSX | T-040, T-036 | Users can trigger and download all MVP formats | Unassigned |
| T-044 | P0 | Add frontend validation hints and error banners | T-038, T-040 | API and validation errors are understandable for users | Unassigned |
| T-045 | P0 | Build end-to-end smoke test: upload -> review -> export | T-043 | Automated smoke test passes on local stack | Unassigned |
| T-046 | P0 | Curate benchmark dataset (invoice + receipt variants) | T-001 | Dataset includes clean/noisy/rotated/multi-layout samples | Unassigned |
| T-047 | P0 | Implement extraction quality evaluation script | T-046, T-026 | Script outputs precision/recall by field and document type | Unassigned |
| T-048 | P0 | Add regression thresholds for extraction quality in CI | T-047 | CI fails when quality drops below agreed thresholds | Unassigned |
| T-049 | P0 | Add integration tests for queue retries and failure states | T-019, T-020 | Retry and dead-letter behavior verified by tests | Unassigned |
| T-050 | P1 | Add role-based authorization checks (Admin/Editor/Viewer) | T-012 | Protected endpoints enforce role checks with tests | Unassigned |
| T-051 | P1 | Add document retention policy and hard-delete job | T-012 | Retention rules configurable and deletions auditable | Unassigned |
| T-052 | P1 | Add structured logging sink and request correlation IDs | T-020 | Logs queryable by request and job IDs | Unassigned |
| T-053 | P1 | Add metrics instrumentation (latency, queue depth, error rate) | T-020 | Metrics exposed and sampled in local dashboard | Unassigned |
| T-054 | P1 | Define alert thresholds for repeated failures and backlog | T-053 | Alert rules documented and test-triggered once | Unassigned |
| T-055 | P1 | Add API rate limiting and abuse guardrails | T-010 | Rate limits active and tested | Unassigned |
| T-056 | P1 | Add audit log views for correction and export events | T-013, T-041, T-036 | Users can inspect historical edits and exports | Unassigned |
| T-057 | P1 | Create staging config profile for managed Postgres/Redis | T-004 | Environment swap works without code changes | Unassigned |
| T-058 | P1 | Implement storage backend switch test (`local` -> `s3`) | T-016 | Same upload/export tests pass under both backends | Unassigned |
| T-059 | P1 | Create local-to-cloud migration runbook | T-057, T-058 | Runbook validated in staging dry run | Unassigned |
| T-060 | P1 | Run pilot with 5 to 10 target users and collect workflow metrics | T-045 | Pilot report includes completion and time-to-value metrics | Unassigned |
| T-061 | P1 | Prioritize beta feedback and create v1.1 hardening backlog | T-060 | Ranked backlog with impact/effort and owners | Unassigned |
| T-062 | P2 | Evaluate direct accounting integrations (QuickBooks/Xero) | T-061 | Integration feasibility doc with API constraints | Unassigned |
| T-063 | P2 | Evaluate automation connectors (Zapier/Make) | T-061 | Connector architecture and cost tradeoff documented | Unassigned |
| T-064 | P2 | Plan payments/subscriptions implementation | T-061 | Billing PRD exists as separate document | Unassigned |

## Milestone Mapping

| Milestone | Required Tasks |
|---|---|
| M1 Local Foundation | T-001 to T-020 |
| M2 Extraction Pipeline | T-021 to T-031 |
| M3 Review and Export | T-032 to T-045 |
| M4 Quality Baseline | T-046 to T-049 |
| M5 Beta Hardening | T-050 to T-061 |

## MVP Exit Checklist

| Check | Pass Criteria |
|---|---|
| Accuracy | Invoice >= 92 percent and receipt >= 88 percent on benchmark set |
| Performance | P95 processing latency < 12 seconds per page |
| Reliability | Retry logic and failure handling pass integration tests |
| Usability | Pilot users complete upload -> review -> export with >= 80 percent success |
| Security | Role checks and retention/delete workflows validated |
