param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "[backend] setup: validating Python runtime..."
& $pythonCmd --version
if ($LASTEXITCODE -ne 0) {
    throw "Python is required for backend tooling."
}

Write-Host "[backend] setup: installing backend dependencies..."
Push-Location $backendDir
try {
    & $pythonCmd -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency install failed."
    }
} finally {
    Pop-Location
}

Write-Host "[backend] setup complete."
