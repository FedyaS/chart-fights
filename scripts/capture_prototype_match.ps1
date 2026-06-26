<#
.SYNOPSIS
  Verification plan step 5: prototype match pytest x2.
  Captures all output to {SCRATCH}/prototype-match.log
#>
param(
    [string]$ScratchDir = "$env:TEMP\grok-goal-fd94c9f2e9b4\implementer"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logFile = Join-Path $ScratchDir "prototype-match.log"
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null
Set-Content -Path $logFile -Value "" -Encoding utf8

function Write-Log($msg) {
    Add-Content -Path $logFile -Value $msg -Encoding utf8
    Write-Host $msg
}

function Run-Match($label) {
    Write-Log "=== $label ==="
    Write-Log "CMD: python -m pytest backend/tests/test_prototype_match.py -v --tb=short"
    Push-Location $projectRoot
    try {
        $out = python -m pytest backend/tests/test_prototype_match.py -v --tb=short 2>&1
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

Write-Log "=== capture_prototype_match.ps1 start (fresh log) ==="
Write-Log "Project: $projectRoot"

Run-Match "PROTOTYPE MATCH RUN 1"
Run-Match "PROTOTYPE MATCH RUN 2"

Write-Log "=== capture_prototype_match.ps1 SUCCESS ==="