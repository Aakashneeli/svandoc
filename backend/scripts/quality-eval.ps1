param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $repoRoot
try {
    $env:PYTHONPATH = "backend/src"
    & $pythonCmd -m svandoc_backend.quality_eval
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
