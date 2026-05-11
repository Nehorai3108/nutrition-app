# Entity Relationship Diagram (ERD)

## Entities and Relationships

```
┌──────────────────┐         ┌──────────────────────┐
│   UserProfile    │         │   NutritionTargets    │
├──────────────────┤         ├──────────────────────┤
│ user_id (PK)     │────1:N──│ user_id (FK)          │
│ name             │         │ bmr_kcal              │
│ gender           │         │ tdee_kcal             │
│ date_of_birth    │         │ target_calories_kcal  │
│ height_cm        │         │ protein_g             │
│ weight_kg        │         │ carbs_g               │
│ activity_level   │         │ fat_g                 │
│ goal             │         │ calculation_method    │
│ created_at       │         └──────────────────────┘
│ updated_at       │
└──────────────────┘
        │
        │ 1:N
        ▼
┌──────────────────┐         ┌──────────────────────┐
│  InventoryItem   │         │     FoodItem          │
├──────────────────┤         ├──────────────────────┤
│ inv_item_id (PK) │──N:1───│ food_id (PK)          │
│ food_id (FK)     │         │ name_he               │
│ quantity         │         │ name_en               │
│ unit             │         │ category              │
│ expiry_date      │         │ nutrition_per_100g    │
│ added_at         │         │ default_unit          │
│ updated_at       │         │ aliases_he[]          │
└──────────────────┘         │ aliases_en[]          │
                             │ is_custom             │
                             └──────────────────────┘
                                      │
                                      │ N:M (via MealItem)
                                      ▼
┌──────────────────┐         ┌──────────────────────┐
│    MealPlan      │         │      MealItem         │
├──────────────────┤         ├──────────────────────┤
│ plan_id (PK)     │────1:N──│ food_id (FK)          │
│ user_id (FK)     │         │ food_name             │
│ run_id (FK)      │         │ quantity_g            │
│ plan_date        │         │ calories_kcal         │
│ target_cal       │         │ protein_g             │
│ created_at       │         │ carbs_g               │
└──────────────────┘         │ fat_g                 │
        │                    │ from_inventory        │
        │ 1:N                │ inventory_item_id(FK) │
        ▼                    └──────────────────────┘
┌──────────────────┐
│      Meal        │
├──────────────────┤
│ meal_type        │────1:N──▶ MealItem
│ items[]          │
└──────────────────┘


┌──────────────────┐         ┌──────────────────────┐
│    RunState      │         │    StageResult        │
├──────────────────┤         ├──────────────────────┤
│ run_id (PK)      │────1:N──│ stage                 │
│ user_id (FK)     │         │ status                │
│ started_at       │         │ started_at            │
│ completed_at     │         │ completed_at          │
│ is_success       │         │ duration_ms           │
└──────────────────┘         │ output_artifact_key   │
        │                    │ error_message         │
        │ 1:N                └──────────────────────┘
        ▼
┌──────────────────┐         ┌──────────────────────┐
│  DecisionGate    │         │  ArtifactRecord       │
├──────────────────┤         ├──────────────────────┤
│ decision_id (PK) │         │ artifact_key (PK)     │
│ run_id (FK)      │         │ run_id (FK)           │
│ stage            │         │ stage                 │
│ decision_type    │         │ artifact_type         │
│ reason           │         │ description           │
│ status           │         │ file_path             │
│ resolution       │         │ data (JSON)           │
│ created_at       │         │ created_at            │
└──────────────────┘         └──────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│ InventorySnapshot    │     │  InventoryChange      │
├──────────────────────┤     ├──────────────────────┤
│ snapshot_id (PK)     │     │ change_id (PK)        │
│ run_id (FK)          │     │ inv_item_id (FK)      │
│ timestamp            │     │ food_id (FK)          │
│ items[] (FK→InvItem) │     │ action                │
└──────────────────────┘     │ qty_before            │
                             │ qty_after             │
                             │ qty_delta             │
                             │ reason                │
                             │ run_id (FK)           │
                             │ timestamp             │
                             └──────────────────────┘
```

## Relationship Summary

| From             | To                | Cardinality | Via           |
|------------------|-------------------|-------------|---------------|
| UserProfile      | NutritionTargets  | 1:N         | user_id       |
| UserProfile      | MealPlan          | 1:N         | user_id       |
| UserProfile      | InventoryItem     | 1:N         | (implicit)    |
| UserProfile      | RunState          | 1:N         | user_id       |
| FoodItem         | InventoryItem     | 1:N         | food_id       |
| FoodItem         | MealItem          | 1:N         | food_id       |
| MealPlan         | Meal              | 1:N         | composition   |
| Meal             | MealItem          | 1:N         | composition   |
| RunState         | StageResult       | 1:N         | composition   |
| RunState         | DecisionGate      | 1:N         | run_id        |
| RunState         | ArtifactRecord    | 1:N         | run_id        |
| RunState         | InventorySnapshot | 1:N         | run_id        |
| InventoryItem    | InventoryChange   | 1:N         | inv_item_id   |

## Data Classification

| Entity            | Class          | Retention          |
|-------------------|----------------|--------------------|
| UserProfile       | Source         | Permanent          |
| FoodItem          | Source         | Permanent          |
| InventoryItem     | Source         | Permanent          |
| NutritionTargets  | Derived        | Per-run + latest   |
| MealPlan          | Derived        | Per-run            |
| RunState          | Execution      | Configurable       |
| ArtifactRecord    | Derived/Cache  | Per retention policy |
| InventorySnapshot | Snapshot       | Per retention policy |
| InventoryChange   | Log            | Permanent (audit)  |
| DecisionGate      | Execution      | Per-run            |
