param(
    [string]$CsvPath = "datasets/pilot/v1/pilot_sessions.csv",
    [string]$OutputPath = ".local-sandbox/pilot-metrics.json"
)

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
    $env:PYTHONPATH = "src"
    $resolvedCsv = if ([System.IO.Path]::IsPathRooted($CsvPath)) { $CsvPath } else { Join-Path $repoRoot $CsvPath }
    $resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $repoRoot $OutputPath }
    $outputDir = Split-Path -Parent $resolvedOutput
    if ($outputDir) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }

    & $pythonCmd -m svandoc_backend.pilot_metrics --csv $resolvedCsv --out $resolvedOutput
    if ($LASTEXITCODE -ne 0) { throw "pilot metrics evaluation failed" }
} finally {
    Pop-Location
}

