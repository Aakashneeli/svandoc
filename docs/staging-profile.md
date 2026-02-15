# Staging Config Profile

Last updated: 2026-02-15

This project supports config-only environment swap for staging via profile overlays.

## Files

1. Base config: `.env`
2. Staging overlay template: `.env.staging.example`
3. Staging overlay runtime file: `.env.staging` (create from template)

## How It Works

Startup scripts call `Get-DotEnvMap` from `scripts/lib/env.ps1`.

1. Load base `.env` (or `.env.example` fallback)
2. Resolve profile:
- `APP_ENV` process env var, else
- `APP_ENV` from `.env`, else
- `local`
3. If profile is not `local`, overlay values from:
- `.env.<profile>`, else
- `.env.<profile>.example`

No service code changes are required to switch local vs staging settings.

## Example

```powershell
Copy-Item .env.staging.example .env.staging
$env:APP_ENV = "staging"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```
