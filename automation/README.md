# BiteFit Automation Pipeline

5 agents that run overnight (18:00–06:00 IST) to push the app toward MVP.

## Pipeline Flow

```
[Designer]  ──┐
[Structure] ──┤──► briefs/ ──► [Implementor] ──► code changes
[Research]  ──┘                      │
                                     ▼
                              [Audit Agent]
                                     │
                              audit_feedback.md
                                     │
                              ──► [Implementor] (next run fixes)
```

## Agents & Schedule (IST = UTC+3)

| # | Agent | Schedule | Output |
|---|-------|----------|--------|
| 1 | Designer | Every 3 days, 18:00 IST | `storage_agents/briefs/design_brief.md` |
| 2 | Structure | Every 7 days, 19:00 IST | `storage_agents/briefs/structure_brief.md` |
| 3 | Research | Every 3 days, 20:00 IST | `storage_agents/briefs/research_brief.md` |
| 4 | Implementor | Daily, 22:00 IST | code changes + `implementor_log.md` |
| 5 | Audit | Daily, 02:00 IST | `storage_agents/briefs/audit_feedback.md` |

## First-Time Setup

### Step 0 — Authenticate for headless runs (REQUIRED, one-time)

Task Scheduler launches `claude` as a fresh background process. Your interactive
login does NOT carry over, so a fresh process reports "Not logged in." Fix it once
with a long-lived subscription token:

```powershell
claude setup-token
```

This opens a browser, you log in with your Claude subscription, and it persists a
long-lived token that all future `claude` runs (including scheduled tasks) will use.
Verify it worked:

```powershell
cd "C:\Users\User\Desktop\אפליקציית תזונאי"
claude --print --permission-mode acceptEdits --allowedTools Write "Write 'ok' to automation/logs/_authcheck.txt"
```
If `automation/logs/_authcheck.txt` appears, auth is good.

### Step 1 — Register the schedule

```powershell
cd "C:\Users\User\Desktop\אפליקציית תזונאי"
.\automation\setup_scheduler.ps1
```
(No Admin required — tasks run as the current user. Tasks only fire while you are
logged on, which is correct since the token lives in your user profile.)

### Step 2 — Verify

Open **Task Scheduler** → Task Scheduler Library → **BiteFit** to confirm 5 tasks.

## Run an Agent Manually

```powershell
cd "C:\Users\User\Desktop\אפליקציית תזונאי"
.\automation\run_agent.ps1 -Agent 01_designer
```

## Output Files

All briefs land in `storage_agents/briefs/`:
- `design_brief.md` — UI/UX improvement tasks
- `structure_brief.md` — App store readiness tasks
- `research_brief.md` — New feature suggestions
- `implementor_log.md` — What was implemented (append-only)
- `audit_feedback.md` — Latest audit verdict

Logs per run: `automation/logs/<agent>_<timestamp>.log`

## Tweaking Agent Prompts

Edit files in `automation/prompts/`. Changes take effect on next scheduled run.
No need to re-run `setup_scheduler.ps1` — it only registers timing, not prompts.

## Removing the Schedule

```powershell
Get-ScheduledTask -TaskPath "\BiteFit\" | Unregister-ScheduledTask -Confirm:$false
```
