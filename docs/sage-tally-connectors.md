# Sage and Tally Connector Strategy

Last updated: 2026-02-16

## Overview

svanDoc now supports phased Sage and Tally exports through `POST /api/documents/{id}/export`.

Supported formats:
- `sage`
- `tally`

## Sage (Phased Strategy)

Current phase:
- `phase_1_file_exchange`

Behavior:
1. Call export endpoint with `{"format":"sage"}`.
2. API generates a Sage strategy artifact (`*.sage-plan.json`) with:
- connector phase roadmap,
- document summary mapping (counterparty, reference, totals, tax, currency),
- migration path to direct API sync (`phase_2_partner_api`).

Intent:
- Deliver immediate integration path for finance teams without OAuth setup.
- Preserve a deterministic artifact that can be reviewed and audited.

## Tally (Import Package)

Behavior:
1. Call export endpoint with `{"format":"tally"}`.
2. API generates a `.tally.zip` package containing:
- `manifest.json`
- `voucher.xml`
- `summary.csv`

Import path:
- Use `voucher.xml` as primary Tally import input.
- Use `summary.csv` for reconciliation and quick validation.

## API Example

```json
POST /api/documents/{document_id}/export
{
  "format": "sage"
}
```

```json
POST /api/documents/{document_id}/export
{
  "format": "tally"
}
```

## Notes

- Both formats persist to `export_artifacts` with format values `sage` and `tally`.
- Artifacts are included in audit history via `GET /api/documents/{id}/audit`.
