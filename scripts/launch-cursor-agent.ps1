<#
.SYNOPSIS
  Helper to launch Cursor Agent with proper context for chart-fights.

.DESCRIPTION
  Opens key design files in Cursor and starts the terminal agent.
  Use from project root or pass -Task to focus a specific cursor-task.

.EXAMPLE
  .\scripts\launch-cursor-agent.ps1
  .\scripts\launch-cursor-agent.ps1 -Task "002-time-and-tempo"
#>
param(
    [string]$Task,
    [string]$Prompt
)

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "Opening chart-fights in Cursor with design context..." -ForegroundColor Cyan

# Open main specs + research
cursor docs/design/GDD.md docs/design/game-mechanics-spec.md docs/research/data-sources-initial.md --reuse-window

if ($Task) {
    $taskFile = "docs/cursor-tasks/task-$Task.md"
    if (Test-Path $taskFile) {
        Write-Host "Opening specific task: $taskFile" -ForegroundColor Green
        cursor $taskFile --reuse-window
    } else {
        Write-Warning "Task file not found: $taskFile"
    }
}

if (-not $Prompt -and $Task) {
    $Prompt = "Implement docs/cursor-tasks/task-$Task.md in backend/ and frontend/. Run tests after changes. Respect .cursorrules and opened design docs."
}

Write-Host "`nStarting Cursor Agent in terminal..." -ForegroundColor Yellow
Write-Host "The agent will respect .cursorrules and the opened design docs." -ForegroundColor Gray
if ($Prompt) {
    Write-Host "Prompt: $Prompt" -ForegroundColor Gray
    $Prompt | cursor agent 2>&1 | Tee-Object -FilePath (Join-Path $projectRoot "scratch\cursor-agent-$(Get-Date -Format 'yyyyMMdd_HHmmss').log")
} else {
    cursor agent 2>&1 | Tee-Object -FilePath (Join-Path $projectRoot "scratch\cursor-agent-$(Get-Date -Format 'yyyyMMdd_HHmmss').log")
}
