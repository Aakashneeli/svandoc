param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Push-Location $backendDir
try {
    $env:PYTHONPATH = "src"
    & python -m unittest discover -s tests -p "test_*.py"
    if ($LASTEXITCODE -ne 0) { throw "backend tests failed" }
} finally {
    Pop-Location
}
