param(
    [string]$InputPath = "datasets/pilot/v1/feedback_items.json",
    [string]$OutputPath = ".local-sandbox/v1_1-hardening-backlog.json"
)

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $backendDir
try {
    $env:PYTHONPATH = "src"
    $resolvedInput = if ([System.IO.Path]::IsPathRooted($InputPath)) { $InputPath } else { Join-Path $repoRoot $InputPath }
    $resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $repoRoot $OutputPath }
    $outputDir = Split-Path -Parent $resolvedOutput
    if ($outputDir) {
        New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    }

    & $pythonCmd -m svandoc_backend.feedback_prioritization --input $resolvedInput --out $resolvedOutput
    if ($LASTEXITCODE -ne 0) { throw "feedback prioritization failed" }
} finally {
    Pop-Location
}

