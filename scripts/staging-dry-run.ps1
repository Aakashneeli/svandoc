param(
    [string]$Profile = "staging",
    [switch]$SkipMigrations,
    [switch]$SkipReadiness,
    [string]$ApiReadyUrl = "http://127.0.0.1:8000/ready"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repoRoot "scripts/lib/env.ps1")

$envMap = Get-DotEnvMap -ProfileName $Profile

$requiredKeys = @(
    "DATABASE_URL",
    "REDIS_URL",
    "STORAGE_BACKEND",
    "NEXT_PUBLIC_API_BASE_URL",
    "VLLM_BASE_URL",
    "VLLM_FALLBACK_BASE_URL"
)

$missing = @()
foreach ($key in $requiredKeys) {
    $value = Get-EnvValue -Map $envMap -Key $key -DefaultValue ""
    if (-not $value) {
        $missing += $key
        continue
    }
    Set-Item -Path ("Env:{0}" -f $key) -Value $value
}

if ($missing.Count -gt 0) {
    throw ("Missing required staging keys: {0}" -f ($missing -join ", "))
}

$storageBackend = (Get-EnvValue -Map $envMap -Key "STORAGE_BACKEND" -DefaultValue "local").ToLowerInvariant()
if ($storageBackend -eq "s3") {
    $requiredS3 = @("S3_BUCKET", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
    $missingS3 = @()
    foreach ($key in $requiredS3) {
        $value = Get-EnvValue -Map $envMap -Key $key -DefaultValue ""
        if (-not $value) {
            $missingS3 += $key
            continue
        }
        Set-Item -Path ("Env:{0}" -f $key) -Value $value
    }
    if ($missingS3.Count -gt 0) {
        throw ("Missing required S3 keys for staging: {0}" -f ($missingS3 -join ", "))
    }
}

$migrationStatus = "skipped"
if (-not $SkipMigrations) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "backend/scripts/migrate.ps1") -ShowCurrent
    if ($LASTEXITCODE -ne 0) {
        throw "Staging dry run migration failed."
    }
    $migrationStatus = "passed"
}

$readinessStatus = "skipped"
if (-not $SkipReadiness) {
    try {
        $readyResponse = Invoke-WebRequest -Uri $ApiReadyUrl -UseBasicParsing -TimeoutSec 5
        if ($readyResponse.StatusCode -ge 200 -and $readyResponse.StatusCode -lt 300) {
            $readinessStatus = "passed"
        } else {
            $readinessStatus = "failed"
        }
    } catch {
        $readinessStatus = "failed"
    }
}

$result = @{
    profile = $Profile
    checked_at = (Get-Date).ToString("o")
    migration = $migrationStatus
    readiness = $readinessStatus
    storage_backend = $storageBackend
    required_keys_checked = $requiredKeys
}

$localDir = Join-Path $repoRoot ".local"
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$outputPath = Join-Path $localDir "staging-dry-run.json"
$result | ConvertTo-Json -Depth 4 | Out-File -Encoding UTF8 $outputPath

Write-Host ("staging dry run result written to {0}" -f $outputPath)
Write-Host ($result | ConvertTo-Json -Depth 4)
