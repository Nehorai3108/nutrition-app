# Performance Guidelines

Owner: Agent 7 — Data & Performance Infrastructure

## Core Principles

1. **Behavior-Preserving**: All optimizations MUST produce identical business outputs
2. **No Business Logic Changes**: Never simplify calculations at the cost of accuracy
3. **Audit Integrity**: Never delete audit-critical data

## Data Classification

| Class          | Description                      | Examples                          | Retention         |
|----------------|----------------------------------|-----------------------------------|-------------------|
| **Source**     | Primary data entered by users    | UserProfile, FoodItem, Inventory  | Permanent         |
| **Derived**    | Calculated from source data      | NutritionTargets, MealPlan        | Per-run + latest  |
| **Cache**      | Pre-computed views for speed     | Dashboard summaries               | Ephemeral         |
| **Log**        | Execution records                | Stage logs, change log            | 90 days           |
| **Debug**      | Development-time outputs         | Verbose traces                    | 7 days            |
| **Snapshot**   | Point-in-time state captures     | InventorySnapshot                 | Per retention policy |

## Duplicate Prevention

1. Each artifact has a **single canonical location**
2. If an artifact exists in multiple places, one is `source` and others are `derived`
3. The `DataManager.check_duplicates()` method runs during health checks
4. Cleanup strategy removes stale derived artifacts per retention policy

## Efficient Rerun Strategy

1. Each stage stores its output as a registered artifact
2. On rerun of stage N, stages 1..N-1 are skipped if their outputs exist
3. The orchestrator supports `rerun_stage(run_id, stage)` for point reruns
4. No unnecessary dependencies between stages — each reads from context, not from prior stage objects

## Dashboard Performance

1. Dashboard reads **lightweight summaries**, not raw run states
2. `run_index.json` holds per-run metadata for fast listing
3. Full run states loaded only on drill-down
4. Health panel aggregates cached metrics, not live scans

## Storage Optimization

1. JSON files with proper indentation for debuggability
2. One directory per run under `storage/runs/{run_id}/`
3. Index files at `storage/run_index.json` and `storage/artifacts/artifacts_index.json`
4. Future: consider SQLite for >1000 runs

## Caching Strategy

1. Food catalog: loaded in-memory on init (small dataset)
2. Run summaries: cached in `_run_index` dict
3. Dashboard health metrics: computed on-demand (fast enough for Phase 1)
4. Future: add TTL-based cache for frequently accessed data

## Future-Proofing

The storage design supports:
- **Multiple users**: user_id is part of all entities
- **OCR/image ingestion**: FoodItem accepts `source` field for data origin
- **Large food catalogs**: search is indexed by normalized names
- **Analytics**: run_index provides structured query base
- **API/mobile**: all agents return serializable dicts
- **More runs**: directory-per-run keeps filesystem flat

## Performance Monitoring

1. Every stage records `duration_ms`
2. Dashboard shows `slowest_stages` ranking
3. `storage_bytes` / `storage_mb` tracked in health panel
4. `failed_runs` / `success_rate` visible in health panel
