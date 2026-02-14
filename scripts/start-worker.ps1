param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repoRoot "scripts/lib/env.ps1")

$envMap = Get-DotEnvMap
$mode = Get-EnvValue -Map $envMap -Key "WORKER_START_MODE" -DefaultValue "placeholder"
$heartbeat = Get-EnvValue -Map $envMap -Key "WORKER_HEARTBEAT_SECONDS" -DefaultValue "2"
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

$workerDir = Join-Path $repoRoot "worker"
if (-not (Test-Path $workerDir)) {
    throw "Missing worker directory: $workerDir"
}

Set-Location $repoRoot

if ($mode -eq "celery") {
    Write-Host "[worker] Starting Celery mode"
    celery -A app.worker_app worker -l info
    exit $LASTEXITCODE
}

Write-Host "[worker] Starting placeholder mode"
$env:WORKER_HEARTBEAT_SECONDS = $heartbeat
& $pythonCmd (Join-Path $workerDir "dev_worker.py")
exit $LASTEXITCODE
