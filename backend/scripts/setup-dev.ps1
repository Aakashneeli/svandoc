param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "[backend] setup: validating Python runtime..."
python --version
if ($LASTEXITCODE -ne 0) {
    throw "Python is required for backend tooling."
}

Write-Host "[backend] setup: no third-party install required at this stage."
Write-Host "[backend] setup complete."
