# Retention & Cleanup Policy

Owner: Agent 7 — Data & Performance Infrastructure

## Retention Rules

| Data Class   | Default Retention | Cleanup Action       | Notes                          |
|--------------|-------------------|----------------------|--------------------------------|
| Source       | Permanent         | Never auto-delete    | UserProfile, FoodItem, Inventory |
| Derived      | 30 days           | Delete file + registry | NutritionTargets, MealPlan (per-run) |
| Cache        | 7 days            | Delete file + registry | Dashboard pre-computed views   |
| Log          | 90 days           | Delete file + registry | Execution logs                 |
| Debug        | 7 days            | Delete file + registry | Verbose debug output           |
| Snapshot     | 30 days           | Delete file + registry | InventorySnapshot              |

## Special Rules

1. **Latest derived artifacts** are NEVER deleted — only older per-run copies
2. **InventoryChange (audit log)** is permanent — never subject to cleanup
3. **DecisionGate records** retained as long as their parent RunState exists
4. **Run states**: retained 30 days by default, but failed runs kept 90 days for diagnosis

## Cleanup Procedure

1. `DataManager.cleanup_stale_artifacts(policy)` is the single entry point
2. Always run with `dry_run: True` first to preview deletions
3. Deletions remove both file and registry entry
4. Cleanup runs are themselves logged

## Policy Configuration

```python
default_policy = {
    "max_age_days": 30,        # derived/cache/snapshot
    "keep_source": True,       # never delete source data
    "keep_logs_days": 90,      # log retention
    "dry_run": True,           # preview mode by default
}
```

## No-Delete Guarantees

The following are NEVER deleted automatically:
- UserProfile records
- FoodItem records (catalog + custom)
- InventoryItem current state
- InventoryChange audit trail
- The latest NutritionTargets per user
- The latest MealPlan per user
