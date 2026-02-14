# svanDoc Canonical Extraction Schemas

This directory contains canonical JSON schemas for svanDoc extraction outputs.

## Goals

1. Keep API and export contracts stable across model and prompt changes.
2. Make validation deterministic in backend, worker, and integrations.
3. Version schema changes explicitly to prevent silent breaking changes.

## Versioning Policy

Schema versions follow semantic versioning:

1. Major (`X.0.0`): breaking structural changes (rename/remove required fields, type changes).
2. Minor (`0.X.0`): backward-compatible additions (new optional fields, non-breaking enums).
3. Patch (`0.0.X`): documentation-only updates or constraints that do not break valid payloads.

### Directory convention

- `v1/` contains all schema files with `schema_version = "1.0.0"`.
- Future breaking versions use `v2/`, `v3/`, etc.

### File convention

- `invoice.schema.json`
- `receipt.schema.json`

### Compatibility rules

1. Backend must emit `schema_version` in every extraction payload.
2. Consumers should reject payloads where `schema_version` is unknown.
3. Any schema change requires:
- updated example payloads,
- contract tests,
- changelog entry in this directory.
