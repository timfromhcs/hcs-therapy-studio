<#
.SYNOPSIS
    External 30-minute checkpoint reminder for the HCS Therapy Studio work session.

.DESCRIPTION
    Runs *outside* the agent as a detached PowerShell process. Every N minutes it
    appends one line to a log, updates a JSON state file, and optionally raises a
    Windows notification. The agent reads the state file at natural boundaries and
    reports what the reminder said — it never sleeps or polls.

    Deliberately NOT a scheduled task: `AGENTS.md` §8.5 allows exactly one
    autostart entry (`OpenCodeLocalStack`), and a reminder that outlives its
    session would be a second one. This process has a hard deadline and exits.

.PARAMETER Minutes
    Interval between reminders. Default 30.

.PARAMETER Hours
    Hard stop after this many hours, so a forgotten process cannot linger.

.PARAMETER LogPath
    Where reminders are appended. Defaults to a file in the user's TEMP.

.PARAMETER Once
    Emit a single reminder and exit. Used by the test suite.

.EXAMPLE
    pwsh -File scripts/ops/reminder.ps1 -Minutes 30 -Hours 8
#>
[CmdletBinding()]
param(
    [int]$Minutes = 30,
    [int]$Hours = 8,
    [string]$LogPath = (Join-Path $env:TEMP 'hcs-reminders.log'),
    [string]$StatePath = (Join-Path $env:TEMP 'hcs-reminder-state.json'),
    [switch]$Once
)

$ErrorActionPreference = 'Stop'

if ($Minutes -lt 1) { throw 'Minutes must be at least 1.' }
if ($Hours -lt 1) { throw 'Hours must be at least 1.' }

function Write-Reminder {
    param([int]$Count, [datetime]$StartedAt)

    $now = Get-Date
    $stamp = $now.ToString('yyyy-MM-dd HH:mm:ss')
    $next = $now.AddMinutes($Minutes)
    $line = "[$stamp] reminder #$Count  next in ${Minutes}min  (session started $($StartedAt.ToString('HH:mm')))"

    Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8

    $state = [ordered]@{
        count          = $Count
        last_reminder  = $now.ToString('o')
        next_reminder  = $next.ToString('o')
        interval_min   = $Minutes
        session_start  = $StartedAt.ToString('o')
        log            = $LogPath
        pid            = $PID
    }
    $state | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding utf8

    # Best-effort toast. Failure is irrelevant: the log is the contract.
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
        $balloon = New-Object System.Windows.Forms.NotifyIcon
        $balloon.Icon = [System.Drawing.SystemIcons]::Information
        $balloon.BalloonTipTitle = 'HCS Therapy Studio'
        $balloon.BalloonTipText = "Checkpoint #$Count — next in $Minutes min"
        $balloon.Visible = $true
        $balloon.ShowBalloonTip(5000)
        Start-Sleep -Milliseconds 200
        $balloon.Dispose()
    } catch {
        # Headless session or no notification area. Not an error.
    }

    Write-Output $line
}

$startedAt = Get-Date
$deadline = $startedAt.AddHours($Hours)

if ($Once) {
    Write-Reminder -Count 1 -StartedAt $startedAt
    return
}

# First line goes out immediately so the log proves the process is alive, then
# the interval starts. A reminder process that is silent for 30 minutes before
# its first line is indistinguishable from one that died.
$count = 1
Write-Reminder -Count $count -StartedAt $startedAt

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds ($Minutes * 60)
    if ((Get-Date) -ge $deadline) { break }
    $count++
    Write-Reminder -Count $count -StartedAt $startedAt
}

Add-Content -LiteralPath $LogPath -Encoding utf8 `
    -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] reminder process finished after $count reminders"
