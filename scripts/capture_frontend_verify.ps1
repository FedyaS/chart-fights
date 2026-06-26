<#
.SYNOPSIS
  Verification plan step 4: frontend controller verify x2.
  Captures all output to {SCRATCH}/frontend-verify.log
#>
param(
    [string]$ScratchDir = "$env:TEMP\grok-goal-fd94c9f2e9b4\implementer"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $projectRoot "frontend"
$logFile = Join-Path $ScratchDir "frontend-verify.log"
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null
Set-Content -Path $logFile -Value "" -Encoding utf8

function Write-Log($msg) {
    Add-Content -Path $logFile -Value $msg -Encoding utf8
    Write-Host $msg
}

function Run-Frontend($label) {
    Write-Log "=== $label ==="
    Write-Log "CMD: node scripts/verify-controller.cjs"
    Push-Location $frontend
    try {
        $out = node scripts/verify-controller.cjs 2>&1
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

Write-Log "=== capture_frontend_verify.ps1 start (fresh log) ==="
Write-Log "Project: $projectRoot"

Run-Frontend "FRONTEND RUN 1"
Run-Frontend "FRONTEND RUN 2"

Write-Log "=== capture_frontend_verify.ps1 SUCCESS ==="