param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repoRoot "scripts/lib/env.ps1")

$envMap = Get-DotEnvMap
$port = Get-EnvValue -Map $envMap -Key "API_PORT" -DefaultValue "8000"
$mode = Get-EnvValue -Map $envMap -Key "API_START_MODE" -DefaultValue "placeholder"
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

$backendDir = Join-Path $repoRoot "backend"
if (-not (Test-Path $backendDir)) {
    throw "Missing backend directory: $backendDir"
}

Set-Location $backendDir

if ($mode -eq "fastapi") {
    Write-Host "[api] Starting FastAPI mode on port $port"
    & $pythonCmd -m uvicorn svandoc_backend.main:app --app-dir src --host 127.0.0.1 --port $port --reload
    exit $LASTEXITCODE
}

Write-Host "[api] Starting placeholder mode on port $port"
& $pythonCmd -m http.server $port --bind 127.0.0.1 --directory $backendDir
exit $LASTEXITCODE
