# Custom Extraction Templates

Last updated: 2026-02-16

## Overview

svanDoc supports reusable extraction templates for recurring invoice and receipt layouts.

Capabilities:
1. Define template metadata (`name`, `doc_type`)
2. Store schema definition JSON
3. Store field mappings (`target_field -> source_path`)
4. Apply template mapping to an extraction payload

## API

1. `POST /api/templates`
- Creates a template for the current workspace (`x-team-id`).

2. `GET /api/templates`
- Lists workspace templates.

3. `POST /api/documents/{document_id}/templates/apply`
- Applies selected template mapping to document extraction.
- Output is stored under `structured_payload.template_output`.

## Review UI

The Review page includes a new "Extraction Templates" panel:
- create template (name, doc type, schema JSON, mapping JSON)
- choose saved template
- apply template to current document

## Mapping behavior

- Each mapping entry resolves a source path (for example `vendor.name`) from canonical payload.
- Missing source paths are reported in `template_output.missing_paths`.
- Resolved values are written to `template_output.mapped_fields`.
