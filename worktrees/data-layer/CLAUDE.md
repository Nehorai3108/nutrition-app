# Nutrition App — Architecture Guide

## Agent Architecture
- Agent 1 (Contracts): Domain models, schemas, validation
- Agent 2 (Nutrition): BMR/TDEE calculation, macro targets
- Agent 3 (Food): Food catalog, search, matching
- Agent 4 (Inventory): Inventory management, availability, deduction
- Agent 5 (Planner): Deterministic meal plan generation
- Agent 6 (AI): Text formatting, summaries (not source of truth)
- Agent 7 (Data): Persistence, artifact management, cleanup
- Agent 8 (Director): Identifies system gaps, creates tasks, NEVER executes
- Agent 9 (Critic): Reviews completed tasks, approves/rejects, re-queues failures

## Task Flow
Director writes → Agents execute → Critic reviews → loop

## Storage
- `storage_agents/tasks/` — pending_tasks.json, completed_tasks.json, verdicts.json
- `storage_agents/audit/director_reports/` — Director analysis reports
- `storage_agents/audit/` — director_log.txt, critic_log.txt, audit.log
- `storage_agents/plans/` — Saved meal plans

## Workflow Pipeline Order
1. CREATE_USER_PROFILE
2. CALCULATE_TARGETS
3. RESOLVE_FOODS
4. CHECK_INVENTORY
5. GENERATE_MEAL_PLAN
6. PRESENT_DECISION
7. CONFIRM
8. DEDUCT_INVENTORY
9. PERSIST_RUN_ARTIFACTS
10. DIRECTOR_ANALYSIS (Agent 8)
11. CRITIC_REVIEW (Agent 9)
