<#
.SYNOPSIS
  Verification plan step 2: harness driver x2 + pytest test_sim x2.
  Captures all output to {SCRATCH}/sim-test.log
#>
param(
    [string]$ScratchDir = "$env:TEMP\grok-goal-fd94c9f2e9b4\implementer"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logFile = Join-Path $ScratchDir "sim-test.log"
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null
Set-Content -Path $logFile -Value "" -Encoding utf8

function Write-Log($msg) {
    Add-Content -Path $logFile -Value $msg -Encoding utf8
    Write-Host $msg
}

function Run-Cmd($label, $cmd, $cmdArgs) {
    Write-Log "=== $label ==="
    Write-Log "CMD: $cmd $($cmdArgs -join ' ')"
    Push-Location $projectRoot
    try {
        $out = & $cmd @cmdArgs 2>&1
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        $out | ForEach-Object { Write-Log $_ }
        Write-Log "EXIT_CODE=$code"
        if ($code -ne 0) {
            Write-Log "ERROR: $label failed exit=$code"
            exit 1
        }
    } finally {
        Pop-Location
    }
}

Write-Log "=== capture_sim_test.ps1 start (fresh log) ==="
Write-Log "Project: $projectRoot"

Run-Cmd "HARNESS RUN 1" "python" @("backend/tests/test_sim.py")
Run-Cmd "HARNESS RUN 2" "python" @("backend/tests/test_sim.py")
Run-Cmd "PYTEST RUN 1" "python" @("-m", "pytest", "backend/tests/test_sim.py", "-q", "--tb=line")
Run-Cmd "PYTEST RUN 2" "python" @("-m", "pytest", "backend/tests/test_sim.py", "-q", "--tb=line")

Write-Log "=== capture_sim_test.ps1 SUCCESS ==="