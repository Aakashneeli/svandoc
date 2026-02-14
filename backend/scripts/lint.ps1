param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Push-Location $backendDir
try {
    & python tools/lint_backend.py
    if ($LASTEXITCODE -ne 0) { throw "backend lint checks failed" }
} finally {
    Pop-Location
}
