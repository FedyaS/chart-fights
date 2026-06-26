<#
.SYNOPSIS
  Orchestrator: runs all verification plan capture scripts in order.
  Produces auditable evidence in {SCRATCH}.
#>
param(
    [string]$ScratchDir = "$env:TEMP\grok-goal-fd94c9f2e9b4\implementer"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $projectRoot "scripts"
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null

function Invoke-Step($name, $script) {
    Write-Host "`n========== $name ==========" -ForegroundColor Cyan
    & $script -ScratchDir $ScratchDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $name exit=$LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK: $name" -ForegroundColor Green
}

Write-Host "=== capture_all_verification.ps1 ===" -ForegroundColor Yellow
Write-Host "ScratchDir: $ScratchDir"

Invoke-Step "Step 1: Data fetch" (Join-Path $scripts "capture_data_run.ps1")
Invoke-Step "Step 2: Sim tests" (Join-Path $scripts "capture_sim_test.ps1")
Invoke-Step "Step 3: Backend launch" (Join-Path $scripts "capture_backend_launch.ps1")
Invoke-Step "Step 4: Frontend verify" (Join-Path $scripts "capture_frontend_verify.ps1")
Invoke-Step "Step 5: Prototype match" (Join-Path $scripts "capture_prototype_match.ps1")

Write-Host "`n========== Step 6: Cursor delegation ==========" -ForegroundColor Cyan
$delegateLog = Join-Path $ScratchDir "cursor-delegate.log"
Set-Content -Path $delegateLog -Value "=== cursor delegation $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -Encoding utf8
& (Join-Path $scripts "launch-cursor-agent.ps1") `
    -Task "007-frontend-streaming" `
    -Prompt "Review frontend WS wiring; run frontend/scripts/verify-controller.cjs after changes." `
    2>&1 | Tee-Object -FilePath $delegateLog -Append
Write-Host "OK: Step 6 (cursor delegation logged)" -ForegroundColor Green

Write-Host "`n=== capture_all_verification.ps1 SUCCESS ===" -ForegroundColor Green
Write-Host "Evidence in: $ScratchDir"