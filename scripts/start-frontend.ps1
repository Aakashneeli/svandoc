param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repoRoot "scripts/lib/env.ps1")

$envMap = Get-DotEnvMap
$port = Get-EnvValue -Map $envMap -Key "FRONTEND_PORT" -DefaultValue "3000"
$mode = Get-EnvValue -Map $envMap -Key "FRONTEND_START_MODE" -DefaultValue "placeholder"

$frontendDir = Join-Path $repoRoot "frontend"
if (-not (Test-Path $frontendDir)) {
    throw "Missing frontend directory: $frontendDir"
}

Set-Location $frontendDir

if ($mode -eq "nextjs") {
    Write-Host "[frontend] Starting Next.js mode on port $port"
    npm run dev -- --port $port
    exit $LASTEXITCODE
}

Write-Host "[frontend] Starting placeholder mode on port $port"
python -m http.server $port --bind 127.0.0.1 --directory $frontendDir
exit $LASTEXITCODE
