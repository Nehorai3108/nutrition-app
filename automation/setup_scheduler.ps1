# setup_scheduler.ps1 — Register BiteFit automation agents in Windows Task Scheduler
# Run once as Administrator (right-click PowerShell > Run as Administrator)
# Schedule: 18:00-06:00 IST (Israel Standard Time = UTC+3)
#   IST 18:00 = UTC 15:00
#   IST 19:00 = UTC 16:00
#   IST 20:00 = UTC 17:00
#   IST 22:00 = UTC 19:00
#   IST 02:00 = UTC 23:00 (previous day UTC = next day IST)

$ProjectRoot = "C:\Users\User\Desktop\אפליקציית תזונאי"
$RunScript   = "$ProjectRoot\automation\run_agent.ps1"
$PwshExe     = "pwsh.exe"  # PowerShell 7

# Check if running as admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Not running as Administrator. Some tasks may fail to register."
    Write-Warning "Re-run this script as Administrator for best results."
}

function Register-BiteFitTask {
    param(
        [string]$TaskName,
        [string]$Agent,
        [string]$TriggerTime,   # UTC time HH:mm
        [string]$Schedule,      # Daily / Weekly / custom
        [int]$DaysInterval = 1
    )

    $Action = New-ScheduledTaskAction `
        -Execute $PwshExe `
        -Argument "-NonInteractive -WindowStyle Hidden -File `"$RunScript`" -Agent $Agent" `
        -WorkingDirectory $ProjectRoot

    # Create trigger based on schedule type
    if ($DaysInterval -eq 1) {
        $Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime
    } else {
        # Repeat every N days by using a daily trigger with interval
        $Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime -DaysInterval $DaysInterval
    }

    $Settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable

    # Use current user — no Admin required
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    $Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal `
        -Description "BiteFit automation: $Agent"

    # Register (overwrite if exists)
    Register-ScheduledTask -TaskName $TaskName -TaskPath "\BiteFit\" -InputObject $Task -Force | Out-Null
    Write-Host "  Registered: $TaskName  (triggers at $TriggerTime UTC every $DaysInterval day(s))"
}

Write-Host ""
Write-Host "=== BiteFit Automation Scheduler Setup ==="
Write-Host "All times are UTC (Israel time = UTC+3)"
Write-Host ""

# Agent 1 — Designer: every 3 days at 18:00 IST (15:00 UTC)
Register-BiteFitTask `
    -TaskName "BiteFit-01-Designer" `
    -Agent "01_designer" `
    -TriggerTime "15:00" `
    -DaysInterval 3

# Agent 2 — Structure: every 7 days at 19:00 IST (16:00 UTC)
Register-BiteFitTask `
    -TaskName "BiteFit-02-Structure" `
    -Agent "02_structure" `
    -TriggerTime "16:00" `
    -DaysInterval 7

# Agent 3 — Research: every 3 days at 20:00 IST (17:00 UTC)
Register-BiteFitTask `
    -TaskName "BiteFit-03-Research" `
    -Agent "03_research" `
    -TriggerTime "17:00" `
    -DaysInterval 3

# Agent 4 — Implementor: daily at 22:00 IST (19:00 UTC)
Register-BiteFitTask `
    -TaskName "BiteFit-04-Implementor" `
    -Agent "04_implementor" `
    -TriggerTime "19:00" `
    -DaysInterval 1

# Agent 5 — Audit: daily at 02:00 IST next day (23:00 UTC)
Register-BiteFitTask `
    -TaskName "BiteFit-05-Audit" `
    -Agent "05_audit" `
    -TriggerTime "23:00" `
    -DaysInterval 1

Write-Host ""
Write-Host "=== Done! Tasks registered under \BiteFit\ folder ==="
Write-Host ""
Write-Host "View tasks: Open Task Scheduler > Task Scheduler Library > BiteFit"
Write-Host "Run manually: Right-click any task > Run"
Write-Host ""
Write-Host "To remove all tasks:"
Write-Host '  Get-ScheduledTask -TaskPath "\BiteFit\" | Unregister-ScheduledTask -Confirm:$false'
Write-Host ""

# Show summary
Write-Host "=== Registered Tasks ==="
Get-ScheduledTask -TaskPath "\BiteFit\" 2>$null | ForEach-Object {
    $NextRun = ($_ | Get-ScheduledTaskInfo).NextRunTime
    Write-Host "  $($_.TaskName)  ->  Next run: $NextRun"
}
