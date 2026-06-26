<#
.SYNOPSIS
  Verification plan step 1: dry-run, live fetch x2, parquet/index counts, loader spot-check.
  Captures all output to {SCRATCH}/data-run.log
#>
param(
    [string]$ScratchDir = "$env:TEMP\grok-goal-fd94c9f2e9b4\implementer"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logFile = Join-Path $ScratchDir "data-run.log"
New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null
Set-Content -Path $logFile -Value "" -Encoding utf8

function Write-Log($msg) {
    Add-Content -Path $logFile -Value $msg -Encoding utf8
    Write-Host $msg
}

function Run-Fetch($label, $argString) {
    Write-Log "=== $label ==="
    Write-Log "CMD: python scripts/fetch_historical_data.py $argString"
    $fetchArgs = $argString.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
    Push-Location $projectRoot
    try {
        $out = python scripts/fetch_historical_data.py @fetchArgs 2>&1
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        $out | ForEach-Object { Write-Log $_ }
        Write-Log "EXIT_CODE=$code"
        if ($code -ne 0) {
            Write-Log "ERROR: fetch failed exit=$code"
            exit 1
        }
    } finally {
        Pop-Location
    }
}

function Write-Counts($label) {
    Write-Log "--- $label ---"
    $parquetCount = (Get-ChildItem (Join-Path $projectRoot "data\arenas\*.parquet") -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Log "parquet_files=$parquetCount"
    Push-Location $projectRoot
    try {
        $loaderOut = python -c @"
import json
from pathlib import Path
idx = json.loads(Path('data/arenas_index.json').read_text())
print(f'index_entries={len(idx)}')
import sys
sys.path.insert(0, 'backend')
from app.arena import load_arena
a = load_arena('AAPL_00000')
print(f'loader_arena=AAPL_00000 close0={a[\"bars\"][0][\"close\"]} bars={len(a[\"bars\"])}')
"@ 2>&1
        $loaderOut | ForEach-Object { Write-Log $_ }
        if ($LASTEXITCODE -ne 0) { exit 1 }
    } finally {
        Pop-Location
    }
}

Write-Log "=== capture_data_run.ps1 start (fresh log) ==="
Write-Log "Project: $projectRoot"

Run-Fetch "DATA RUN 1 (dry-run)" "--test --dry-run"
Run-Fetch "DATA RUN 2 (live write)" "--test"
Write-Counts "POST-RUN COUNTS (after live write 1)"
Run-Fetch "DATA RUN 3 (live write repeat)" "--test"
Write-Counts "POST-RUN COUNTS (after live write 2)"

Write-Log "=== capture_data_run.ps1 SUCCESS ==="