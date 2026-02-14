# svanDoc MVP Scope Freeze

Last updated: 2026-02-14
Status: Approved
Approval source: Product owner approved PRD direction in working session on 2026-02-14.

## Objective

Lock a narrow MVP scope that proves core value: invoice and receipt extraction with a human-review flow and reliable exports.

## In Scope (MVP)

1. Upload single and batch files (`PDF`, `PNG`, `JPG`, `TIFF`, `HEIC`).
2. OCR extraction for invoices and receipts.
3. Confidence scoring and low-confidence review flow.
4. Side-by-side review UI with inline correction.
5. Export formats: `JSON`, `CSV`, `XLSX`.
6. Searchable document library and processing status tracking.
7. Basic team roles: Admin, Editor, Viewer.

## Out of Scope (MVP)

1. Payment and subscription systems.
2. Direct accounting sync (QuickBooks, Xero, Sage).
3. ERP connectors.
4. Healthcare-specific extraction workflows.
5. Public API platform and external developer onboarding.
6. Enterprise SSO/SAML, SOC2 program execution, and data residency controls.

## Scope Guardrails

1. Do not add new document categories before invoice/receipt quality targets are met.
2. Do not add integrations that increase support burden before review/export flow is stable.
3. Prioritize extraction accuracy, correction UX, and operational reliability over feature breadth.

## Exit Criteria for Scope Change

Scope may be expanded only after all conditions are met:

1. MVP quality thresholds are met on benchmark and pilot datasets.
2. Upload -> review -> export completion rate is stable with pilot users.
3. Retry/error handling is operational and monitored.
4. Post-MVP tasks are prioritized against customer feedback and team capacity.
