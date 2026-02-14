param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pidPath = Join-Path $repoRoot ".local/pids.json"

if (-not (Test-Path $pidPath)) {
    Write-Host "No pid file found. Nothing to stop."
    exit 0
}

$state = Get-Content $pidPath -Raw | ConvertFrom-Json

foreach ($proc in $state.processes) {
    $procId = [int]$proc.pid
    $running = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($running) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host ("Stopped {0} (PID {1})" -f $proc.name, $procId)
        } catch {
            Write-Host ("Failed to stop {0} (PID {1}): {2}" -f $proc.name, $procId, $_.Exception.Message)
        }
    }
}

Remove-Item -Force $pidPath
Write-Host "Local services stopped."
