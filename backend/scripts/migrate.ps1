param(
    [string]$Target = "head",
    [switch]$ShowCurrent
)

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
    $env:PYTHONPATH = "src"
    & $pythonCmd -m alembic upgrade $Target
    if ($LASTEXITCODE -ne 0) { throw "database migration failed" }

    if ($ShowCurrent) {
        & $pythonCmd -m alembic current
        if ($LASTEXITCODE -ne 0) { throw "failed to read current migration revision" }
    }
} finally {
    Pop-Location
}
