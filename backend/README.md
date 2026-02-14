# Backend Package

This package will host the FastAPI application.

## Planned responsibilities

1. Document upload and metadata endpoints.
2. Job orchestration and status endpoints.
3. Extraction read/update endpoints.
4. Export endpoints and artifact tracking.

## Planned stack

- Python 3.11
- FastAPI
- PostgreSQL
- Redis (queue integration)

## Developer tooling

Commands:

```powershell
powershell -ExecutionPolicy Bypass -File backend/scripts/setup-dev.ps1
powershell -ExecutionPolicy Bypass -File backend/scripts/lint.ps1
powershell -ExecutionPolicy Bypass -File backend/scripts/test.ps1
```

Optional formatter:

```powershell
powershell -ExecutionPolicy Bypass -File backend/scripts/format.ps1
```

Tooling currently uses Python stdlib scripts in `backend/tools/` so no third-party install is required yet.

## Placeholder

Service implementation starts in `T-010` and related tasks.
