# Local Setup Guide (No Docker)

Last updated: 2026-02-14

This guide sets up svanDoc for local-first development on a clean machine.

## 1. Required Software

1. Node.js 20 LTS
2. Python 3.11
3. PostgreSQL 16
4. Redis 7
5. Git

## 2. Install Steps (Windows)

### Node.js 20 LTS

1. Install Node.js 20 LTS from the official installer.
2. Verify:

```powershell
node --version
npm --version
```

### Python 3.11

1. Install Python 3.11 and enable "Add Python to PATH".
2. Verify:

```powershell
python --version
pip --version
```

### PostgreSQL 16

1. Install PostgreSQL 16.
2. Create database `svandoc`.
3. Verify:

```powershell
psql --version
psql -U postgres -h localhost -p 5432 -d postgres -c "SELECT version();"
```

### Redis 7

1. Install Redis 7.
2. Start Redis service.
3. Verify:

```powershell
redis-cli ping
```

Expected response: `PONG`

## 3. Project Setup

From repository root:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` if your local credentials/ports differ from defaults.

Minimum local values to verify:

1. `DATABASE_URL`
2. `REDIS_URL`
3. `STORAGE_BACKEND=local`
4. `LOCAL_STORAGE_PATH`
5. `API_PORT` and `FRONTEND_PORT`

## 4. Startup

Use one-command startup script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Stop all services:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

## 5. Clean Machine Validation Checklist

Run these checks in order:

1. `node --version` returns Node 20.x
2. `python --version` returns Python 3.11.x
3. `psql --version` returns PostgreSQL 16.x
4. `redis-cli ping` returns `PONG`
5. `Copy-Item .env.example .env` succeeds
6. `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1` starts API, worker, and frontend processes
7. `Invoke-WebRequest http://localhost:8000` returns HTTP response
8. `Invoke-WebRequest http://localhost:3000` returns HTTP response
9. `powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1` stops all local service processes

If all checks pass, local setup is ready for the next implementation tasks.
