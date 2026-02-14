param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
    & $pythonCmd tools/format_backend.py
    if ($LASTEXITCODE -ne 0) { throw "backend format step failed" }
} finally {
    Pop-Location
}
