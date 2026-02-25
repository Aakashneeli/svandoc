param()

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$repoRoot = Split-Path -Parent $backendDir
$venvPython = Join-Path $repoRoot "myvenv/Scripts/python.exe"
$pythonCmd = if ($IsWindows -and (Test-Path $venvPython)) { $venvPython } else { "python" }
$runnerScript = Join-Path $backendDir "tools/run_backend_tests.py"
$runMode = if ($env:BACKEND_TEST_RUN_MODE) { $env:BACKEND_TEST_RUN_MODE.Trim().ToLowerInvariant() } else { "module-timeout" }
$moduleTimeoutSeconds = if ($env:BACKEND_TEST_MODULE_TIMEOUT_SECONDS) { $env:BACKEND_TEST_MODULE_TIMEOUT_SECONDS } else { "180" }
$testPattern = if ($env:BACKEND_TEST_PATTERN) { $env:BACKEND_TEST_PATTERN } else { "test_*.py" }
$moduleFilter = if ($env:BACKEND_TEST_MODULE_FILTER) { $env:BACKEND_TEST_MODULE_FILTER } else { "" }

Push-Location $backendDir
try {
    $env:PYTHONPATH = "src"
    if ($runMode -eq "discover") {
        & $pythonCmd -m unittest discover -s tests -p $testPattern
    } else {
        $runnerArgs = @(
            $runnerScript,
            "--python-cmd", $pythonCmd,
            "--pattern", $testPattern,
            "--module-timeout-seconds", $moduleTimeoutSeconds
        )
        if ($moduleFilter -ne "") {
            $runnerArgs += @("--module-filter", $moduleFilter)
        }
        & $pythonCmd @runnerArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "backend tests failed" }
} finally {
    Pop-Location
}
