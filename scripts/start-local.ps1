param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $repoRoot "scripts/lib/env.ps1")

$envMap = Get-DotEnvMap
$apiPort = [int](Get-EnvValue -Map $envMap -Key "API_PORT" -DefaultValue "8000")
$frontendPort = [int](Get-EnvValue -Map $envMap -Key "FRONTEND_PORT" -DefaultValue "3000")

$localDir = Join-Path $repoRoot ".local"
$pidPath = Join-Path $localDir "pids.json"
New-Item -ItemType Directory -Force -Path $localDir | Out-Null

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$ScriptPath
    )
    $proc = Start-Process `
        -FilePath "powershell" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) `
        -WorkingDirectory $repoRoot `
        -PassThru
    return @{
        name = $Name
        pid = $proc.Id
        script = $ScriptPath
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

if (Test-Path $pidPath) {
    throw "Existing pid file found at $pidPath. Run scripts/stop-local.ps1 first."
}

$apiScript = Join-Path $repoRoot "scripts/start-api.ps1"
$frontendScript = Join-Path $repoRoot "scripts/start-frontend.ps1"
$workerScript = Join-Path $repoRoot "scripts/start-worker.ps1"

$started = @()
$started += Start-ManagedProcess -Name "api" -ScriptPath $apiScript
$started += Start-ManagedProcess -Name "frontend" -ScriptPath $frontendScript
$started += Start-ManagedProcess -Name "worker" -ScriptPath $workerScript

$state = @{
    started_at = (Get-Date).ToString("o")
    api_port = $apiPort
    frontend_port = $frontendPort
    processes = $started
}
$state | ConvertTo-Json -Depth 4 | Out-File -Encoding UTF8 $pidPath

$apiReady = Wait-HttpReady -Url ("http://127.0.0.1:{0}" -f $apiPort)
$frontendReady = Wait-HttpReady -Url ("http://127.0.0.1:{0}" -f $frontendPort)
$workerPid = ($started | Where-Object { $_.name -eq "worker" }).pid

if (-not $apiReady -or -not $frontendReady -or -not (Get-Process -Id $workerPid -ErrorAction SilentlyContinue)) {
    Write-Host "Startup failed. Cleaning up launched processes..."
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts/stop-local.ps1") | Out-Null
    throw "Local startup check failed."
}

Write-Host "svanDoc local services started."
Write-Host ("API:      http://127.0.0.1:{0}" -f $apiPort)
Write-Host ("Frontend: http://127.0.0.1:{0}" -f $frontendPort)
Write-Host ("Worker PID: {0}" -f $workerPid)
