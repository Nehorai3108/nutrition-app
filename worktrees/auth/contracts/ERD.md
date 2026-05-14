# Entity Relationship Diagram — MVP 1
### Produced by: Agent 1 | Status: FINAL
### Last updated: 2026-03-24

> Legend:
>   PK  = Primary Key
>   FK  = Foreign Key
>   *   = Required field
>   ?   = Optional (nullable) field
>   [V] = Virtual / computed — not stored independently

---

## Entity Diagram

```
 ┌───────────────────────────────────────────────────────────────┐
 │                          USER                                 │
 │───────────────────────────────────────────────────────────────│
 │ PK  id *                   UUID                               │
 │     email *                STRING  (unique)                   │
 │     name *                 STRING  (1–100 chars)              │
 │     age *                  INT     (10–120)                   │
 │     gender *               ENUM    (male|female|other)        │
 │     height_cm *            FLOAT   (50–250)                   │
 │     weight_kg *            FLOAT   (20–300)                   │
 │     activity_level *       ENUM    (5 values)                 │
 │     goal *                 ENUM    (3 values)                 │
 │     calorie_target_override?  INT  (800–6000 | null)          │
 │     dietary_restrictions?  ARRAY[ENUM]  (default [])          │
 │     subscription_tier?     ENUM    (free|basic|premium)       │
 │     created_at?            DATETIME                           │
 │     updated_at?            DATETIME                           │
 └───────────────────┬───────────────────────┬───────────────────┘
                     │ 1                     │ 1
                     │ has many              │ has exactly one
                     ▼                       ▼
 ┌─────────────────────────────┐   ┌──────────────────────────────┐
 │          MEAL_PLAN          │   │          INVENTORY            │
 │─────────────────────────────│   │──────────────────────────────│
 │ PK  id *          UUID      │   │ PK  id *         UUID        │
 │ FK  user_id *     UUID ─────┼──►│ FK  user_id *    UUID        │
 │     date *        DATE      │   │     updated_at?  DATETIME    │
 │     calorie_target * INT    │   └──────────────┬───────────────┘
 │     status?       ENUM      │                  │ 1
 │     created_at?   DATETIME  │                  │ contains many
 │     updated_at?   DATETIME  │                  ▼
 └──────────────┬──────────────┘   ┌──────────────────────────────────┐
                │ 1                │         INVENTORY_ITEM            │
                │ contains many    │──────────────────────────────────│
                ▼                  │ FK  food_item_id?  UUID  ───────┐ │
 ┌─────────────────────────────┐   │     quantity *     FLOAT        │ │
 │            MEAL             │   │     unit *         ENUM         │ │
 │─────────────────────────────│   │     is_custom_entry? BOOL       │ │
 │ PK  meal_id *     UUID      │   │     custom_item_name? STRING    │ │
 │ FK  meal_plan_id* UUID      │   │     added_at?      DATETIME     │ │
 │     meal_type *   ENUM      │   └─────────────────────────────────┼─┘
 │     name?         STRING    │                                     │
 └──────────────┬──────────────┘                                     │ references (FK)
                │ 1                                                   │
                │ contains many                                       │
                ▼                                                     ▼
 ┌──────────────────────────────┐   ┌─────────────────────────────────────┐
 │          MEAL_ITEM           │   │              FOOD_ITEM               │
 │──────────────────────────────│   │─────────────────────────────────────│
 │ FK  food_item_id * UUID ─────┼──►│ PK  id *               UUID         │
 │     quantity_g *   FLOAT     │   │     name *              STRING       │
 │ [V] calories       FLOAT     │   │     brand?              STRING       │
 │ [V] protein_g      FLOAT     │   │     calories_per_100g * FLOAT       │
 │ [V] carbs_g        FLOAT     │   │     protein_per_100g *  FLOAT       │
 │ [V] fat_g          FLOAT     │   │     carbs_per_100g *    FLOAT       │
 └──────────────────────────────┘   │     fat_per_100g *      FLOAT       │
                                    │     fiber_per_100g?     FLOAT       │
                                    │     default_serving_g?  FLOAT       │
                                    │     category *          ENUM        │
                                    │     name_translations?  OBJECT      │
                                    │     aliases?            ARRAY[STR]  │
                                    │     is_custom?          BOOL        │
                                    │     created_by_user_id? UUID        │
                                    │     created_at?         DATETIME    │
                                    └─────────────────────────────────────┘


 ┌──────────────────────────────────────────────────────────────────────────┐
 │              NUTRITION_PROFILE  [VIRTUAL — not persisted]                │
 │──────────────────────────────────────────────────────────────────────────│
 │     user_id *         UUID  (references User.id)                         │
 │     bmr *             FLOAT (> 0)                                        │
 │     tdee *            FLOAT (>= bmr)                                     │
 │     calorie_target *  INT   (>= 800)  → copied to MealPlan.calorie_target│
 │     protein_target_g* FLOAT (>= 0)                                       │
 │     carbs_target_g *  FLOAT (>= 0)                                       │
 │     fat_target_g *    FLOAT (>= 0)                                       │
 │                                                                          │
 │  Produced by: Agent 2 (Nutrition Engine)                                 │
 │  Consumed by: Agent 5 (Meal Planning Engine) — read-only                 │
 │  Lifecycle:   Computed on demand, discarded after use                    │
 └──────────────────────────────────────────────────────────────────────────┘
```

---

## Relationship Summary

| From              | To                | Cardinality | Constraint                                              |
|-------------------|-------------------|-------------|----------------------------------------------------------|
| User              | MealPlan          | 1 : many    | FK: MealPlan.user_id → User.id                          |
| User              | Inventory         | 1 : 1       | FK: Inventory.user_id → User.id (unique)                |
| MealPlan          | Meal              | 1 : many    | 1–6 meals per plan; each meal_type appears at most once |
| Meal              | MealItem          | 1 : many    | At least 1 item per meal                                |
| MealItem          | FoodItem          | many : 1    | FK: MealItem.food_item_id → FoodItem.id                 |
| Inventory         | InventoryItem     | 1 : many    | Items array embedded in Inventory document              |
| InventoryItem     | FoodItem          | many : 1    | FK: InventoryItem.food_item_id → FoodItem.id (nullable) |
| FoodItem          | User              | many : 1    | FK: FoodItem.created_by_user_id → User.id (nullable)    |
| User              | NutritionProfile  | 1 : 1       | Virtual — computed from User; not stored                |
| NutritionProfile  | MealPlan          | 1 : 1       | calorie_target copied at plan creation time             |

---

## Field-Level Constraints

| Entity          | Field                   | Constraint                                           | Enforced By                         |
|-----------------|-------------------------|------------------------------------------------------|-------------------------------------|
| User            | email                   | Unique across all users                              | Application layer / DB index        |
| User            | age                     | 10 ≤ age ≤ 120                                       | User model `__post_init__`          |
| User            | height_cm               | 50 ≤ value ≤ 250                                     | User model `__post_init__`          |
| User            | weight_kg               | 20 ≤ value ≤ 300                                     | User model `__post_init__`          |
| User            | calorie_target_override | 800 ≤ value ≤ 6000 if set                            | User model `__post_init__`          |
| FoodItem        | calories_per_100g       | 0 ≤ value ≤ 900 (immutable after creation)           | FoodItem model `__post_init__`      |
| FoodItem        | protein/carbs/fat       | 0 ≤ each value ≤ 100                                 | FoodItem model `__post_init__`      |
| FoodItem        | created_by_user_id      | Required when is_custom = true                       | JSON Schema `if/then`               |
| MealPlan        | date                    | Unique per user (one plan per day)                   | Application layer / DB index        |
| MealPlan        | calorie_target          | 800 ≤ value ≤ 6000                                   | MealPlan model `__post_init__`      |
| MealPlan        | meals count             | 1 ≤ count ≤ 6                                        | MealPlan model `__post_init__`      |
| Meal            | meal_type               | At most one of each type per MealPlan                | Agent 5 (Meal Planning Engine)      |
| MealItem        | calories/protein/carbs/fat | Set ONLY by NutritionEngine.compute_item_macros()  | Contract F2                         |
| MealItem        | quantity_g              | ≥ 1                                                  | MealItem model `__post_init__`      |
| Inventory       | user_id                 | Unique (1 inventory per user)                        | Application layer / DB index        |
| InventoryItem   | quantity                | ≥ 0 (never negative)                                 | InventoryItem model `__post_init__` |
| InventoryItem   | food_item_id            | Null when is_custom_entry = true                     | JSON Schema `if/then/else`          |
| InventoryItem   | custom_item_name        | Required when is_custom_entry = true                 | JSON Schema `if/then`               |
| NutritionProfile| bmr                     | > 0                                                  | NutritionProfile `__post_init__`    |
| NutritionProfile| tdee                    | ≥ bmr                                                | NutritionProfile `__post_init__`    |
| NutritionProfile| calorie_target          | ≥ 800 (safety floor enforced by Agent 2)             | NutritionProfile `__post_init__`    |

---

## Computed (Virtual) Fields

These fields are **never stored as raw values**. They are always recomputed
from their source data when needed.

| Field                    | Entity           | Computation                                              |
|--------------------------|------------------|----------------------------------------------------------|
| `calories`               | MealItem         | `(FoodItem.calories_per_100g / 100) * quantity_g`        |
| `protein_g`              | MealItem         | `(FoodItem.protein_per_100g  / 100) * quantity_g`        |
| `carbs_g`                | MealItem         | `(FoodItem.carbs_per_100g    / 100) * quantity_g`        |
| `fat_g`                  | MealItem         | `(FoodItem.fat_per_100g      / 100) * quantity_g`        |
| `Meal.totals`            | Meal             | `SUM of all MealItem macro values in meal.items`         |
| `MealPlan.totals`        | MealPlan         | `SUM of all Meal.totals in meal_plan.meals`              |
| `MealPlan.calorie_gap`   | MealPlan         | `calorie_target − totals.calories`                       |
| `NutritionProfile`       | (virtual entity) | Computed by Agent 2 from User fields; not persisted       |

---

## Out of Scope — MVP 1

| Feature                          | Reason deferred                      |
|----------------------------------|--------------------------------------|
| Weekly meal planning             | Daily planning first                 |
| Barcode / OCR scanning           | Manual entry only in MVP 1           |
| Food item expiry dates           | Not required for planning            |
| Wearable / fitness tracker data  | Future phase                         |
| Per-meal macro target override   | Global daily target only in MVP 1    |
| Social / sharing features        | Not in product scope                 |
| Multi-user households            | Single-user model only               |
| Unit conversion engine           | Only grams are deductible in MVP 1   |
