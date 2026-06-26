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
    [string]$Task
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

Write-Host "`nStarting Cursor Agent in terminal..." -ForegroundColor Yellow
Write-Host "The agent will respect .cursorrules and the opened design docs." -ForegroundColor Gray

# Start the Cursor agent
cursor agent
