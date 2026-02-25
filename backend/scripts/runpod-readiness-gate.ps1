param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
    $env:PYTHONPATH = "src"
    & $pythonCmd -m svandoc_backend.deploy_gate
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
