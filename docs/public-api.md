# Public REST API

Last updated: 2026-02-16

## Overview

svanDoc now exposes API-key protected public endpoints under `/api/public/*`.

Configured via:

- `PUBLIC_API_KEYS_JSON`

## API key config

Set `PUBLIC_API_KEYS_JSON` to a JSON array:

```json
[
  {
    "id": "client-a",
    "key": "replace-me",
    "scopes": ["documents:write", "jobs:read", "extractions:read", "exports:write"]
  }
]
```

Auth header:

- `x-api-key: <key>`

## Scopes

- `documents:write` -> upload endpoints
- `jobs:read` -> job status endpoints
- `extractions:read` -> extraction read endpoints
- `exports:write` -> export endpoints

Optional wildcard:

- `*` grants all scopes

## Public endpoints

1. `POST /api/public/documents/upload`
2. `GET /api/public/jobs/{job_id}`
3. `GET /api/public/documents/{document_id}/extraction`
4. `POST /api/public/documents/{document_id}/export`

## Error behavior

- Missing/invalid key: `401 UNAUTHORIZED`
- Missing scope: `403 FORBIDDEN`
- Endpoint business validation uses existing svanDoc error envelope semantics.
