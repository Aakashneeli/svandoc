# AGENTS.md - svanDoc Project Context

This file captures project-specific context so future agent sessions stay aligned.

we work inside wsl .

Primary fast-context file:
1. Read `MEMORY.md` first in every new session.
2. Use `tasks.md` as the execution order source of truth.
3. After each completed task, update both `tasks.md` and `MEMORY.md`.

## Project Snapshot

- Project: `svanDoc`
- Product type: intelligent document extraction platform for SMEs
- Current phase: MVP definition and local-first implementation
- Primary problem: reduce manual invoice/receipt data entry time and error rate


## Product Rules

1. Optimize for reliability and usability before breadth of features.
2. Preserve correction audit trail for user trust.
3. Prioritize field-level confidence visibility.
4. Keep extraction schema versioned and backward compatible.

## Technical Baseline

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI (Python 3.11)
- Queue: Redis + Celery
- Database: Supabase
- Storage (dev): local filesystem (or MinIO optional)
- Storage (prod): S3 or Cloudflare R2
- OCR inference: vLLM serving `dots.ocr` (primary) and `Chandra` (fallback)

## Environment Strategy

Development strategy:
1. Run everything locally first (no Docker required initially).
2. Keep infra interfaces abstract (`storage`, `queue`, `inference`) so deployment swaps are config-only.
3. Add Docker files later when deployment hardening starts.

Local-to-production principle:
- No app rewrite should be required.
- Only endpoints/secrets/providers should change via environment variables.

## Data and API Contracts to Protect

Core entities:
- `Document`
- `ProcessingJob`
- `ExtractionResult`
- `UserCorrection`
- `ExportArtifact`

Core endpoints:
- `POST /api/documents/upload`
- `GET /api/jobs/{job_id}`
- `GET /api/documents/{id}/extraction`
- `PATCH /api/documents/{id}/extraction`
- `POST /api/documents/{id}/export`

## Quality Bar

- Accuracy thresholds:
  - invoice >= 92 percent
  - receipt >= 88 percent
- Performance threshold:
  - P95 processing latency < 12 sec/page
- Reliability:
  - retries and dead-letter path implemented
- Usability:
  - users can complete upload -> review -> export without guidance

## Agent Working Preferences for This Repo

1. Read `MEMORY.md` first, then `tasks.md`, then `PRD.md`.
2. Keep tasks dependency-aware; do not start downstream items early.
3. Avoid adding non-MVP scope unless explicitly requested.
4. Add tests for pipeline logic, retry behavior, and export correctness.
5. When adding features, update both `PRD.md` and `tasks.md` if scope changes.
6. Keep `MEMORY.md` current with completed tasks, next tasks, and workflow caveats.
7. Use `uv pip install -r <requirements-file>` for Python dependency installs (do not use plain `pip install`).
8. After each completed task, run relevant tests, update `tasks.md` and `MEMORY.md`, then commit and push before starting the next task.

## Decision Log (Current)

1. Local-first setup is mandatory for early development.
2. Docker will be added later for deployment readiness.
3. Payment/subscription work is intentionally deferred.
4. SME invoice/receipt workflow is the first and only MVP launch segment.
