<#
.SYNOPSIS
  Verification plan step 3: launch uvicorn, run HTTP+WS client, kill, relaunch, repeat.
  Captures all output to {SCRATCH}/backend-launch.log
#>
param(
    [string]$ScratchDir = "$env:TEMP\grok-goal-fd94c9f2e9b4\implementer",
    [int]$Port = 8001
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $projectRoot "backend"
$logFile = Join-Path $ScratchDir "backend-launch.log"
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Write-Host $line
}

Write-Log "=== capture_backend_launch.ps1 start ==="
Write-Log "Project: $projectRoot"
Write-Log "Port: $Port"

function Stop-Server($proc) {
    if ($proc -and -not $proc.HasExited) {
        Write-Log "Stopping uvicorn pid=$($proc.Id)"
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

function Wait-Health($maxSec = 20) {
    $deadline = (Get-Date).AddSeconds($maxSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -Method Get -TimeoutSec 2
            if ($r.status -eq "ok") { return $true }
        } catch {}
        Start-Sleep -Milliseconds 400
    }
    return $false
}

for ($run = 1; $run -le 2; $run++) {
    Write-Log "--- LAUNCH RUN $run ---"
    $uvicornLog = Join-Path $ScratchDir "uvicorn-run$run.log"
    $uvicornErr = Join-Path $ScratchDir "uvicorn-run$run.err.log"
    $proc = Start-Process -FilePath "python" `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port" `
        -WorkingDirectory $backend `
        -RedirectStandardOutput $uvicornLog `
        -RedirectStandardError $uvicornErr `
        -PassThru -NoNewWindow

    Write-Log "Started uvicorn pid=$($proc.Id) log=$uvicornLog"
    if (-not (Wait-Health)) {
        Write-Log "ERROR: health check failed run $run"
        Get-Content $uvicornLog -ErrorAction SilentlyContinue | ForEach-Object { Write-Log "uvicorn: $_" }
        Stop-Server $proc
        exit 1
    }
    Write-Log "Health OK run $run"

    $clientOut = Join-Path $ScratchDir "client-run$run.log"
    python (Join-Path $projectRoot "scripts\backend_launch_client.py") $clientOut $run 2>&1 | ForEach-Object { Write-Log "client: $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR: client failed run $run exit=$LASTEXITCODE"
        Stop-Server $proc
        exit 1
    }
    Get-Content $clientOut -Encoding utf8 | ForEach-Object { Write-Log "client-file: $_" }

    Stop-Server $proc
    if (Test-Path $uvicornLog) {
        Get-Content $uvicornLog -ErrorAction SilentlyContinue | Select-Object -Last 15 | ForEach-Object { Write-Log "uvicorn-tail: $_" }
    }
    Write-Log "--- RUN $run COMPLETE ---"
    Start-Sleep -Seconds 1
}

Write-Log "=== capture_backend_launch.ps1 SUCCESS ==="