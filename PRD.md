# PRD: svanDoc - Intelligent Document Extraction for SMEs (MVP v1)

Last updated: 2026-02-14

## 1. Problem Statement

Small and medium businesses (SMEs) lose significant time every week manually copying data from invoices and receipts into spreadsheets or accounting workflows.

Current alternatives usually fail one of these constraints:
- Too expensive for early-stage or lean SMEs.
- Too technical to self-serve.
- Too generic to produce reliable invoice and receipt extraction without manual cleanup.

svanDoc solves this by giving SMEs a simple upload -> review -> export workflow with reliable structured output and a human correction step where confidence is low.

## 2. Product Vision

Build a practical, affordable document extraction platform that reduces manual bookkeeping effort for SMEs.

One-line value proposition:
`Upload documents. Extract structured data. Review quickly. Export anywhere.`
-
## 3. Product Goals and Success Criteria

### Primary goals (MVP)
- Reduce manual data entry time for invoice and receipt workflows by at least 60 percent.
- Achieve production-usable extraction accuracy for common SME invoice and receipt formats.
- Provide a clear human review experience for low-confidence fields.

### Success criteria (MVP launch gate)
- Invoice field extraction accuracy: at least 92 percent on curated test set.
- Receipt field extraction accuracy: at least 88 percent on curated test set.
- P95 processing latency: under 12 seconds per page in normal load.
- End-to-end task completion (upload -> export) without support: at least 80 percent in beta tests.

## 4. Target Users and Jobs To Be Done

### Primary segment
- SMEs with 5 to 50 employees.
- Teams processing about 100 to 1000 documents per month.
- Current process is manual entry into spreadsheets or basic accounting pipelines.

### Personas
1. Small business owner
- Job: capture invoice totals, due dates, tax amounts quickly.
- Pain: manual copy/paste and errors.

2. Bookkeeper or office admin
- Job: process batches of invoices/receipts and export to spreadsheets.
- Pain: repetitive extraction and correction effort.

3. Operations admin
- Job: maintain searchable document records for audit and reporting.
- Pain: unstructured archives and poor retrieval.

## 5. Scope

### In scope for MVP
1. Upload single and batch files (`PDF`, `PNG`, `JPG`, `TIFF`, `HEIC`).
2. OCR and structured extraction for invoices and receipts.
3. Confidence scoring with human review UI.
4. Exports: `CSV`, `XLSX`, `JSON`.
5. Document library with job status and search by metadata.
6. Team roles: Admin, Editor, Viewer....

### Explicitly out of scope for MVP
1. Payment and subscription workflows.
2. Advanced accounting direct sync (QuickBooks, Xero).
3. ERP integrations.
4. Healthcare-specific extraction flows.
5. Full public developer API platform.

These can be revisited after core extraction workflow is validated.

## 6. Core User Flow (MVP)

1. User uploads one or more invoices or receipts.
2. System validates files and creates asynchronous processing jobs.
3. Worker preprocesses image/pages and runs OCR extraction.
4. Extracted output is normalized into a stable schema.
5. Confidence model flags low-confidence fields.
6. User reviews flagged fields in side-by-side UI and edits if required.
7. User exports validated data to CSV/XLSX/JSON.

## 7. Functional Requirements

### FR-1 Upload and Intake
- Drag-and-drop plus file picker upload.
- Batch upload with per-file status.
- Validate file type, size, and page count limits.
- Generate checksum for dedupe and traceability.

### FR-2 Processing Pipeline
- Preprocessing: deskew, denoise, orientation correction.
- OCR primary model: `dots.ocr`.
- Complex fallback model: `Chandra` for low-confidence or complex layouts.
- Normalize output into canonical invoice/receipt schema.
- Store raw OCR text and structured extraction separately.

### FR-3 Confidence and Validation
- Field-level confidence score for all extracted fields.
- Rule checks for totals, tax math, and date formats.
- Mark fields as `review_required` when confidence below threshold.

### FR-4 Review and Correction UI
- Side-by-side document and extracted data.
- Inline editing for any field.
- Persist user corrections with timestamp and actor.
- Show validation warnings before export.

### FR-5 Export
- Export corrected data to `CSV`, `XLSX`, `JSON`.
- Exports preserve schema and numeric/date fidelity.
- Maintain export history per document/job.

### FR-6 Library and Team Access
- Search documents by vendor, date range, amount, status.
- Role-based permissions for document visibility and edits.
- Track job history and failure reason codes.

## 8. Non-Functional Requirements

### Performance
- P50 processing latency under 6 seconds per page.
- P95 processing latency under 12 seconds per page.
- Queue start delay under 30 seconds at expected MVP load.

### Reliability
- Idempotent processing per document version.
- Automatic retries for transient worker failures (max 3 retries).
- Dead-letter queue path for unrecoverable failures.

### Security and Privacy
- Encrypt traffic in transit using HTTPS/TLS.
- Encrypt document storage at rest.
- Role-based access enforcement on all document endpoints.
- Configurable retention and hard-delete support.

### Observability
- Structured logs with `request_id`, `document_id`, `job_id`.
- Metrics for extraction latency, error rate, and queue depth.
- Basic alert thresholds for sustained failures.

## 9. Technical Architecture

### 9.1 High-level architecture

```
[Next.js Frontend]
      |
      | HTTPS
      v
[FastAPI Backend]
      |
      | enqueue jobs
      v
[Redis + Celery Queue] ---> [Celery Worker(s)]
                                 |
                                 | OCR calls
                                 v
                         [vLLM Inference Service]
                          - dots.ocr (primary)
                          - Chandra (fallback)

[PostgreSQL] stores metadata, results, audit
[Object Storage] stores originals and artifacts
```

### 9.2 Chosen stack (local-first)

| Layer | Choice | MVP Rationale |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS | Fast product iteration and strong UI ecosystem |
| Backend API | FastAPI + Python 3.11 | Async support and Python ML ecosystem |
| Database | PostgreSQL 16 (local dev) | Stable relational model for jobs and extraction results |
| Queue | Redis 7 + Celery | Reliable async orchestration for document processing |
| Storage (dev) | Local filesystem (or MinIO optional) | Zero cloud dependency for local-first development |
| Storage (prod) | S3 or Cloudflare R2 | Durable artifact storage and scalable serving |
| Inference | vLLM service | Efficient serving and model routing |
| OCR Models | dots.ocr primary, Chandra fallback | Cost/quality balance for invoice and receipt workload |
| Auth | Supabase Auth or Clerk (decision during implementation) | Fast team auth with minimal custom work |

### 9.3 Model routing policy (MVP)

1. Run `dots.ocr` by default.
2. Trigger fallback to `Chandra` when:
- confidence score under threshold,
- table structure confidence is low,
- or preprocessing detects complex multi-column layout.
3. Persist both model outputs for debugging when fallback is used.

## 10. Local Environment Setup (No Docker Initially)

This project is built to run fully on a local machine first.

### Required software
- Node.js 20 LTS
- Python 3.11
- PostgreSQL 16
- Redis 7
- Git

### Local services and ports
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Worker: local Celery process

### Environment variables (`.env.example`)

| Variable | Purpose |
|---|---|
| `APP_ENV` | `local` / `staging` / `production` |
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `STORAGE_BACKEND` | `local` or `s3` |
| `LOCAL_STORAGE_PATH` | Local file storage root |
| `S3_BUCKET` | Bucket name for production storage |
| `S3_REGION` | Storage region |
| `S3_ACCESS_KEY_ID` | Storage credentials |
| `S3_SECRET_ACCESS_KEY` | Storage credentials |
| `VLLM_BASE_URL` | OCR inference endpoint |
| `VLLM_API_KEY` | Optional key if protected |
| `OCR_DEFAULT_MODEL` | default model name |
| `OCR_FALLBACK_MODEL` | fallback model name |
| `JWT_SECRET` | Auth token secret if self-managed |
| `MAX_UPLOAD_MB` | Upload limit guardrail |

### Local run sequence
1. Start PostgreSQL and Redis locally.
2. Start backend API.
3. Start Celery worker.
4. Start frontend.
5. Run smoke test: upload sample invoice -> review -> export JSON.

## 11. Data Model (Core Types)

### Document
- `id`
- `team_id`
- `uploaded_by`
- `filename`
- `mime_type`
- `checksum`
- `storage_uri`
- `page_count`
- `created_at`

### ProcessingJob
- `id`
- `document_id`
- `status` (`queued`, `processing`, `review_required`, `completed`, `failed`)
- `attempt_count`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`

### ExtractionResult
- `id`
- `document_id`
- `schema_version`
- `doc_type` (`invoice`, `receipt`)
- `raw_ocr_text`
- `structured_payload` (JSON)
- `confidence_map` (JSON)
- `is_review_required`

### UserCorrection
- `id`
- `document_id`
- `field_path`
- `old_value`
- `new_value`
- `corrected_by`
- `corrected_at`

### ExportArtifact
- `id`
- `document_id`
- `format` (`csv`, `xlsx`, `json`)
- `storage_uri`
- `created_by`
- `created_at`

## 12. API Contracts (MVP)

1. `POST /api/documents/upload`
- Input: multipart file(s), optional `doc_type_hint`
- Output: `document_id[]`, `job_id[]`

2. `GET /api/jobs/{job_id}`
- Output: status, progress, retry count, error details

3. `GET /api/documents/{document_id}/extraction`
- Output: structured payload + confidence map + review flags

4. `PATCH /api/documents/{document_id}/extraction`
- Input: field updates and correction metadata
- Output: updated extraction payload

5. `POST /api/documents/{document_id}/export`
- Input: format (`csv`, `xlsx`, `json`)
- Output: artifact metadata and download URL

## 13. Milestones and Acceptance Gates

### Gate A: Local foundation ready
- Frontend, backend, Postgres, Redis, and worker all run locally.
- Upload endpoint persists documents and creates jobs.

### Gate B: Extraction pipeline ready
- OCR pipeline runs on test invoices/receipts end-to-end.
- Baseline extraction metrics available.

### Gate C: Review and export ready
- Side-by-side review works with inline edits.
- CSV/XLSX/JSON exports pass integrity checks.

### Gate D: Beta readiness
- Monitoring, retries, retention controls, and QA suite in place.
- Beta checklist passed with pilot users.

## 14. Testing Strategy

### Accuracy tests
- Curated dataset with varied invoice and receipt layouts.
- Field-level precision/recall tracking.
- Regression threshold checks in CI.

### Integration tests
- Upload -> process -> review -> export end-to-end.
- Permission checks across Admin/Editor/Viewer roles.
- Retry/dead-letter behavior validation.

### Performance tests
- Batch load tests for queue throughput.
- P50/P95 per-page latency checks under expected concurrency.

## 15. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OCR quality drops on noisy scans | User distrust and rework | Improve preprocessing and route hard cases to fallback model |
| Queue backlog under burst load | Slow user experience | Queue depth monitoring, worker autoscaling path |
| Cost spikes when fallback overused | Margin pressure | Tune routing threshold, optimize preprocessing, monitor fallback ratio |
| Data privacy concerns | Sales friction | Retention controls, clear deletion path, strict access controls |

## 16. Local-to-Production Translation Plan

The local-first stack is intentionally designed to deploy without app rewrites.

### What stays the same
- FastAPI service code and routes.
- Celery task definitions and queue semantics.
- Postgres schema and migrations.
- Frontend product flows.

### What changes at deployment
- `DATABASE_URL`: local Postgres -> managed Postgres (Supabase, Neon, RDS).
- `REDIS_URL`: local Redis -> managed Redis (Upstash, Redis Cloud, Elasticache).
- `STORAGE_BACKEND`: local filesystem -> S3 or Cloudflare R2.
- `VLLM_BASE_URL`: local/staging inference endpoint -> managed GPU runtime (Modal or RunPod).

### Recommended rollout
1. Stage 1: fully local stack.
2. Stage 2: move DB/Redis/storage to managed cloud, keep app local for testing.
3. Stage 3: deploy frontend/API/workers with staged traffic and monitoring.

## 17. Post-MVP Roadmap (v1.1 to v2.0)

This section defines features planned after MVP validation. These are intentionally sequenced so core extraction quality is protected while capability expands.

### 17.1 Connector expansion

1. Spreadsheet and storage connectors
- Google Sheets direct push.
- Google Drive, OneDrive, and Dropbox export sync.

2. Automation connectors
- Outbound webhooks for key events (`job.completed`, `job.failed`, `export.created`).
- Zapier integration.
- Make.com integration.

3. Accounting connectors
- QuickBooks Online.
- Xero.
- Sage (phased).
- Tally-compatible export package (phased).

### 17.2 Platform capabilities

1. Email intake
- Dedicated inbox per workspace for auto-ingestion and processing rules.

2. Public API productization
- API keys, scoped permissions, and rate limits.
- API docs and starter SDKs.

3. Extraction intelligence upgrades
- Custom extraction templates and template learning from corrections.
- Advanced table extraction (multi-page stitching, merged cells, nested headers).
- Handwriting-focused extraction route.
- Expanded multi-language support with automatic language detection.

### 17.3 Enterprise and compliance features

1. Immutable audit trail and exportable audit reports.
2. Approval workflow (`Reviewer` -> `Approver`) for controlled outputs.
3. SSO/SAML and SCIM provisioning.
4. SOC2 readiness controls and operational evidence pipeline.
5. Data residency controls (US/EU region options).
6. Self-hosted/on-prem deployment package.

### 17.4 Commercialization (deferred priority)

1. Usage metering.
2. Payments and subscriptions.
3. Plan enforcement and billing operations.

Commercialization remains intentionally lower priority than extraction quality, integrations, and enterprise trust features.
