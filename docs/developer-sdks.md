# Developer SDK Quickstarts

Last updated: 2026-02-16

## Prerequisites

1. Public API enabled (`T-071`).
2. API key with scopes:
- `documents:write`
- `jobs:read`
- `extractions:read`
- `exports:write`
3. Environment variables:
- `SVANDOC_API_BASE_URL` (staging API base URL)
- `SVANDOC_API_KEY`

## TypeScript starter SDK

Location:
- `sdk/typescript/src/client.ts`

Runnable quickstart:
- `sdk/typescript/examples/quickstart.mjs`

Command:

```powershell
node sdk/typescript/examples/quickstart.mjs
```

## Python starter SDK

Location:
- `sdk/python/svandoc_sdk/client.py`

Runnable quickstart:
- `sdk/python/examples/quickstart.py`

Command:

```powershell
$env:PYTHONPATH="sdk/python"
myvenv\Scripts\python.exe sdk/python/examples/quickstart.py
```
