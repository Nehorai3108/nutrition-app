# run_agent.ps1 — Run a single BiteFit automation agent via Claude CLI
# Usage: .\run_agent.ps1 -Agent 01_designer
# Logs output to automation\logs\

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("01_designer","02_structure","03_research","04_implementor","05_audit")]
    [string]$Agent
)

$ProjectRoot = "C:\Users\User\Desktop\אפליקציית תזונאי"
$PromptsDir  = "$ProjectRoot\automation\prompts"
$LogsDir     = "$ProjectRoot\automation\logs"
$PromptFile  = "$PromptsDir\$Agent.md"

# Ensure logs dir exists
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Force $LogsDir | Out-Null }

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile   = "$LogsDir\${Agent}_${Timestamp}.log"

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Starting agent: $Agent"
Write-Host "Log: $LogFile"

# Check claude CLI is available
$ClaudePath = (Get-Command claude -ErrorAction SilentlyContinue)?.Source
if (-not $ClaudePath) {
    Write-Error "claude CLI not found. Make sure Claude Code is installed and in PATH."
    exit 1
}

# Ensure the long-lived OAuth token is present in this process. Task Scheduler
# normally inherits user env vars, but load it explicitly as a safety net.
if ([string]::IsNullOrEmpty($env:CLAUDE_CODE_OAUTH_TOKEN)) {
    $env:CLAUDE_CODE_OAUTH_TOKEN = [Environment]::GetEnvironmentVariable('CLAUDE_CODE_OAUTH_TOKEN','User')
}
if ([string]::IsNullOrEmpty($env:CLAUDE_CODE_OAUTH_TOKEN)) {
    Write-Error "CLAUDE_CODE_OAUTH_TOKEN not set. Run 'claude setup-token' and set the User env var."
    exit 1
}

# Read the prompt
$Prompt = Get-Content $PromptFile -Raw -Encoding UTF8

# Run claude in print mode (non-interactive), piping the prompt
# --print outputs the response then exits
# --no-conversation disables history
Set-Location $ProjectRoot

$StartTime = Get-Date
"=== BiteFit Agent: $Agent ===" | Out-File $LogFile -Encoding UTF8
"Started: $StartTime" | Out-File $LogFile -Append -Encoding UTF8
"===========================================" | Out-File $LogFile -Append -Encoding UTF8

# Map each agent to the tools it needs.
# Research/Designer/Structure/Audit need file I/O + web; the Implementor also
# needs two safe Bash verify commands. acceptEdits auto-approves file writes.
$AllowedTools = switch ($Agent) {
    "04_implementor" { 'Read Write Edit Glob Grep Bash(python -m py_compile:*) Bash(python -m pytest:*)' }
    default          { 'Read Write Edit Glob Grep WebSearch WebFetch' }
}

# Belt-and-suspenders guard for the implementor: never push or delete unattended.
$DisallowedTools = 'Bash(git push:*) Bash(rm:*) Bash(git reset:*)'

try {
    & claude --print `
        --permission-mode acceptEdits `
        --allowedTools $AllowedTools `
        --disallowedTools $DisallowedTools `
        --max-budget-usd 2.00 `
        $Prompt 2>&1 | Tee-Object -FilePath $LogFile -Append
    $ExitCode = $LASTEXITCODE
} catch {
    "ERROR: $_" | Out-File $LogFile -Append -Encoding UTF8
    $ExitCode = 1
}

$EndTime = Get-Date
$Duration = ($EndTime - $StartTime).TotalMinutes
"===========================================" | Out-File $LogFile -Append -Encoding UTF8
"Finished: $EndTime (${duration}min) ExitCode: $ExitCode" | Out-File $LogFile -Append -Encoding UTF8

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Done. Exit: $ExitCode  Duration: $([math]::Round($Duration,1))min"
exit $ExitCode
