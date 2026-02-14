param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Push-Location $backendDir
try {
    & python tools/format_backend.py
    if ($LASTEXITCODE -ne 0) { throw "backend format step failed" }
} finally {
    Pop-Location
}
