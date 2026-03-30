# Complete Contract Layer — MVP 1
### Produced by: Agent 1 | Status: FINAL
### Last updated: 2026-03-24

> This document is the single authoritative source for all data structures,
> entity contracts, module ownership, and inter-module communication rules.
> No downstream agent may alter a contract without a formal revision from Agent 1.

---

## Table of Contents

1. [Module Ownership Table](#1-module-ownership-table)
2. [User Contract](#2-user-contract)
3. [FoodItem Contract](#3-fooditem-contract)
4. [Inventory Contract](#4-inventory-contract)
5. [MealPlan Contract](#5-mealplan-contract)
6. [NutritionProfile Contract](#6-nutritionprofile-contract)
7. [Inter-Module Flow Contracts](#7-inter-module-flow-contracts)
8. [Frozen Structures](#8-frozen-structures)
9. [Forbidden Cross-Module Calls](#9-forbidden-cross-module-calls)

---

## 1. Module Ownership Table

| Module                  | File                                    | Owner       | Responsibility                                      | Status              |
|-------------------------|-----------------------------------------|-------------|-----------------------------------------------------|---------------------|
| User Profile            | `app/models/user.py`                    | Agent 1     | Field definitions, enums, validation                | FINAL               |
| Food Database Model     | `app/models/food_item.py`               | Agent 1     | Food item structure, nutritional field schema       | FINAL               |
| Meal Plan Model         | `app/models/meal_plan.py`               | Agent 1     | MealPlan, Meal, MealItem, MacroTotals structures    | FINAL               |
| Inventory Model         | `app/models/inventory.py`               | Agent 1     | Inventory + InventoryItem structure                 | FINAL               |
| JSON Schemas            | `contracts/schemas/`                    | Agent 1     | Validation schemas for all entities                 | FINAL               |
| ERD                     | `contracts/ERD.md`                      | Agent 1     | Entity relationships and constraints                | FINAL               |
| API Contracts           | `contracts/api/contracts.md`            | Agent 1     | Inter-module interfaces and ownership boundaries    | FINAL               |
| **Nutrition Engine**    | `app/modules/nutrition_engine.py`       | **Agent 2** | BMR, TDEE, calorie targets, macro targets, safety floors | STUB           |
| **Food Database**       | `app/modules/food_db.py` *(create)*     | **Agent 3** | Food item storage, search, matching, custom items   | NOT STARTED         |
| **Inventory Manager**   | `app/modules/inventory_manager.py`      | **Agent 4** | Inventory CRUD, availability check, deduction       | STUB                |
| **Meal Planning Engine**| `app/modules/meal_planning_engine.py`   | **Agent 5** | Meal generation, food selection, portion sizing     | STUB                |
| AI Layer                | `app/modules/ai_layer.py` *(create)*    | Agent 6     | Meal name generation (cosmetic only)                | NOT STARTED         |
| Payments                | `app/modules/payments.py` *(create)*    | Agent 7     | Subscription management, tier enforcement           | NOT STARTED         |
| Mobile App              | *(separate project)*                    | Agent 8     | UI rendering, user interactions                     | NOT STARTED         |

---

## 2. User Contract

### 2.1 Purpose
Represents a registered user. Provides physical stats to Agent 2 (Nutrition Engine),
dietary preferences to Agent 5 (Meal Planning Engine), and identity to all modules.

### 2.2 Required Fields

| Field            | Type    | Constraints                                                   |
|------------------|---------|---------------------------------------------------------------|
| `id`             | UUID    | Auto-generated (UUID v4). Immutable after creation.           |
| `email`          | string  | Valid email format. Must be unique across all users.          |
| `name`           | string  | 1–100 characters.                                             |
| `age`            | integer | 10–120 inclusive.                                             |
| `gender`         | enum    | `"male"` \| `"female"` \| `"other"`. Affects BMR formula.    |
| `height_cm`      | float   | 50–250 inclusive.                                             |
| `weight_kg`      | float   | 20–300 inclusive.                                             |
| `activity_level` | enum    | See ActivityLevel enum values below.                          |
| `goal`           | enum    | `"lose_weight"` \| `"maintain"` \| `"gain_muscle"`.          |

### 2.3 Optional Fields

| Field                      | Type         | Default  | Constraints                                         |
|----------------------------|--------------|----------|-----------------------------------------------------|
| `calorie_target_override`  | integer\|null| `null`   | 800–6000 kcal. If set, Agent 2 skips TDEE formula. |
| `dietary_restrictions`     | array[enum]  | `[]`     | See DietaryRestriction enum values below.           |
| `subscription_tier`        | enum         | `"free"` | `"free"` \| `"basic"` \| `"premium"`.              |
| `created_at`               | datetime     | now()    | ISO 8601 datetime. Set on creation, immutable.      |
| `updated_at`               | datetime     | now()    | ISO 8601 datetime. Updated on any field change.     |

### 2.4 ActivityLevel Enum Values

| Value                | Description                                |
|----------------------|--------------------------------------------|
| `sedentary`          | Little or no exercise                      |
| `lightly_active`     | Light exercise 1–3 days/week              |
| `moderately_active`  | Moderate exercise 3–5 days/week           |
| `very_active`        | Hard exercise 6–7 days/week              |
| `extra_active`       | Very hard exercise or physical job         |

> **Agent 2 note:** PAL multiplier values per level are Agent 2's responsibility.
> They are NOT defined in this contract.

### 2.5 DietaryRestriction Enum Values

| Value           | Applied By  | Behavior                                          |
|-----------------|-------------|---------------------------------------------------|
| `vegetarian`    | Agent 5     | Exclude meat, fish                                |
| `vegan`         | Agent 5     | Exclude all animal products                       |
| `gluten_free`   | Agent 5     | Exclude gluten-containing items                   |
| `lactose_free`  | Agent 5     | Exclude dairy items                               |
| `halal`         | Agent 5     | Exclude non-halal items                           |
| `kosher`        | Agent 5     | Exclude non-kosher items                          |
| `nut_free`      | Agent 5     | Exclude tree nuts and peanuts                     |

### 2.6 Validation Rules

```
id             → required, UUID v4 format
email          → required, valid email, unique
name           → required, 1 ≤ len ≤ 100
age            → required, 10 ≤ age ≤ 120
gender         → required, one of: male | female | other
height_cm      → required, 50 ≤ height_cm ≤ 250
weight_kg      → required, 20 ≤ weight_kg ≤ 300
activity_level → required, valid ActivityLevel enum value
goal           → required, valid Goal enum value
calorie_target_override → optional; if present: 800 ≤ value ≤ 6000
dietary_restrictions    → optional; array, each item a valid DietaryRestriction
subscription_tier       → optional; one of: free | basic | premium
```

### 2.7 Canonical JSON Example

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "yossi@example.com",
  "name": "Yossi Cohen",
  "age": 32,
  "gender": "male",
  "height_cm": 178,
  "weight_kg": 85,
  "activity_level": "moderately_active",
  "goal": "lose_weight",
  "calorie_target_override": null,
  "dietary_restrictions": [],
  "subscription_tier": "basic",
  "created_at": "2026-03-24T10:00:00Z",
  "updated_at": "2026-03-24T10:00:00Z"
}
```

### 2.8 Field Consumer Map

| Field                      | Consumed By                          |
|----------------------------|--------------------------------------|
| `id`                       | All modules (identity reference)     |
| `age`, `gender`, `height_cm`, `weight_kg`, `activity_level`, `goal`, `calorie_target_override` | Agent 2 only |
| `dietary_restrictions`     | Agent 5 only                         |
| `subscription_tier`        | Agent 7 only                         |
| `email`, `name`            | Agent 8 (display) only               |

---

## 3. FoodItem Contract

### 3.1 Purpose
A food product stored in the database. The **single source of truth** for all
calorie and macro data. All values are per 100g and must never be modified
by the AI layer or by any calculation module.

### 3.2 Required Fields

| Field               | Type   | Constraints                                                  |
|---------------------|--------|--------------------------------------------------------------|
| `id`                | UUID   | Auto-generated (UUID v4). Immutable.                         |
| `name`              | string | 1–150 chars. Primary display name (default language).        |
| `calories_per_100g` | float  | 0–900 kcal. Source of truth. Never AI-modified.              |
| `protein_per_100g`  | float  | 0–100 g. Grams of protein per 100g of food.                  |
| `carbs_per_100g`    | float  | 0–100 g. Grams of carbohydrates per 100g of food.            |
| `fat_per_100g`      | float  | 0–100 g. Grams of fat per 100g of food.                      |
| `category`          | enum   | See FoodCategory enum values below.                          |

### 3.3 Optional Fields

| Field                  | Type         | Default | Constraints                                             |
|------------------------|--------------|---------|---------------------------------------------------------|
| `brand`                | string\|null | `null`  | Max 100 chars.                                          |
| `fiber_per_100g`       | float\|null  | `null`  | 0–100 g.                                                |
| `default_serving_g`    | float\|null  | `null`  | ≥ 1g. Hint for Agent 5 portion sizing.                 |
| `name_translations`    | object\|null | `null`  | See multilingual section (3.5).                         |
| `aliases`              | array[string]| `[]`    | Alternative names for search/matching (Agent 3).        |
| `is_custom`            | boolean      | `false` | `true` = user-added item, not from global DB.           |
| `created_by_user_id`   | UUID\|null   | `null`  | Required when `is_custom = true`. References User.id.   |
| `created_at`           | datetime     | now()   | ISO 8601. Set on creation, immutable.                   |

### 3.4 FoodCategory Enum Values

| Value          | Description                                |
|----------------|--------------------------------------------|
| `protein`      | Meat, fish, eggs, legumes                  |
| `carbohydrate` | Grains, bread, rice, pasta                 |
| `vegetable`    | Non-starchy vegetables                     |
| `fruit`        | Fresh and dried fruits                     |
| `dairy`        | Milk, yogurt, cheese                       |
| `fat_oil`      | Oils, butter, avocado                      |
| `beverage`     | Drinks (excluding water)                   |
| `snack`        | Nuts, seeds, bars, crackers                |
| `condiment`    | Sauces, dressings, spices                  |
| `other`        | Uncategorized items                        |

### 3.5 Multilingual Name Support

The `name_translations` field holds display names for supported locales.
The top-level `name` field always contains the **English** primary name.

```json
"name_translations": {
  "he": "חזה עוף",
  "ar": "صدر الدجاج",
  "fr": "Blanc de poulet"
}
```

**Rules:**
- Keys must be valid BCP-47 language tags (e.g., `"en"`, `"he"`, `"ar"`)
- `"en"` key is redundant (use top-level `name` instead) but tolerated
- Agent 8 (Mobile App) selects the locale key matching the user's device language
- If a translation for the user's locale does not exist → fall back to `name`
- Agent 3 (Food DB) is responsible for populating and maintaining translations

### 3.6 Allowed Units for Inventory Deduction

Inventory items reference a `FoodItem` by `food_item_id`. The valid units
that can be associated with a food item in inventory are:

| Unit     | Symbol | Applies to                          | Deductible in MVP 1 |
|----------|--------|-------------------------------------|---------------------|
| grams    | `g`    | Most solid foods                    | YES                 |
| millilitres | `ml` | Liquids, beverages                 | NO (future)         |
| units    | `units`| Eggs, fruit pieces, bread slices    | NO (future)         |
| tablespoon | `tbsp` | Condiments, oils                  | NO (future)         |
| teaspoon | `tsp`  | Spices, condiments                  | NO (future)         |
| cup      | `cup`  | Cereal, grains (volumetric)         | NO (future)         |

> **MVP 1 rule:** Only `g` (grams) supports automatic inventory deduction.
> All other units are stored but not deducted when a plan is confirmed.

### 3.7 Validation Rules

```
id                  → required, UUID v4
name                → required, 1 ≤ len ≤ 150
calories_per_100g   → required, 0 ≤ value ≤ 900
protein_per_100g    → required, 0 ≤ value ≤ 100
carbs_per_100g      → required, 0 ≤ value ≤ 100
fat_per_100g        → required, 0 ≤ value ≤ 100
category            → required, valid FoodCategory enum value
fiber_per_100g      → optional; if present: 0 ≤ value ≤ 100
default_serving_g   → optional; if present: value ≥ 1
brand               → optional; if present: len ≤ 100
is_custom           → optional; default false
created_by_user_id  → required IF is_custom = true; must be valid User.id
name_translations   → optional; keys = BCP-47 language tags, values = non-empty strings
aliases             → optional; array of strings, each 1–150 chars
```

### 3.8 Canonical JSON Example

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "Chicken Breast",
  "brand": null,
  "calories_per_100g": 165,
  "protein_per_100g": 31,
  "carbs_per_100g": 0,
  "fat_per_100g": 3.6,
  "fiber_per_100g": null,
  "default_serving_g": 150,
  "category": "protein",
  "name_translations": {
    "he": "חזה עוף",
    "ar": "صدر الدجاج"
  },
  "aliases": ["chicken", "grilled chicken", "boiled chicken"],
  "is_custom": false,
  "created_by_user_id": null,
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

## 4. Inventory Contract

### 4.1 Purpose
Tracks the food items a user currently has at home.
Used by Agent 4 (Inventory Manager) to produce an `available_ids` list
for Agent 5 (Meal Planning Engine), and to generate a shopping list
for Agent 8 (Mobile App).

### 4.2 Inventory Document Structure

One document per user. Upserted (not duplicated) on every write.

| Field       | Type              | Required | Constraints                        |
|-------------|-------------------|----------|------------------------------------|
| `id`        | UUID              | YES      | Unique inventory document ID.      |
| `user_id`   | UUID              | YES      | References User.id. Must be unique (1-to-1 with User). |
| `items`     | array[InventoryItem] | YES   | Can be empty `[]`.                 |
| `updated_at`| datetime          | NO       | ISO 8601. Updated on any mutation. |

### 4.3 InventoryItem Structure

| Field           | Type     | Required | Constraints                                              |
|-----------------|----------|----------|----------------------------------------------------------|
| `food_item_id`  | UUID\|null | YES    | References FoodItem.id. See unknown item rules (4.6).    |
| `quantity`      | float    | YES      | ≥ 0. A value of 0 means out of stock (item not removed). |
| `unit`          | enum     | YES      | One of: `g`, `ml`, `units`, `tbsp`, `tsp`, `cup`.       |
| `is_custom_entry`| boolean | NO      | `true` when food_item_id is null (unknown item). Default: `false`. |
| `custom_item_name`| string\|null| NO  | Required when `is_custom_entry = true`. 1–150 chars.     |
| `added_at`      | datetime | NO       | ISO 8601. Set when item is first added.                  |

### 4.4 Quantity Rules

```
quantity ≥ 0          → ALWAYS. Floor is zero, never negative.
quantity = 0          → Item is out of stock. Not removed from inventory.
                        Appears in shopping list when needed.
quantity > 0          → Item is available. Included in available_ids output.
```

### 4.5 Relation to food_item_id

```
food_item_id references FoodItem.id (FK).

If FoodItem exists in DB:
  → is_custom_entry = false
  → custom_item_name = null
  → Inventory deduction is supported (unit = "g" only in MVP 1)
  → Item appears in available_ids output (quantity > 0)

If FoodItem does NOT exist in DB:
  → is_custom_entry = true
  → food_item_id = null
  → custom_item_name = required (user-provided label)
  → Item is EXCLUDED from available_ids (cannot be matched to a MealItem)
  → Item is stored for user reference only — no calorie data available
```

### 4.6 Unknown Item Handling

Unknown items are food products the user has entered manually that do not
match any FoodItem in the database.

**Rules:**
- `food_item_id` is set to `null`
- `is_custom_entry` is set to `true`
- `custom_item_name` must be provided
- Unknown items are **never** passed to Agent 5 in `available_ids`
- Unknown items are **never** used in calorie calculations
- Agent 4 must store them without error, and Agent 8 displays them to the user

### 4.7 Validation Rules

```
Inventory document:
  id          → required, UUID v4
  user_id     → required, UUID v4, must reference valid User
  items       → required, array (empty is valid)

InventoryItem:
  food_item_id     → required only if is_custom_entry = false
  quantity         → required, value ≥ 0
  unit             → required, valid enum value
  is_custom_entry  → optional, default false
  custom_item_name → required if is_custom_entry = true; 1 ≤ len ≤ 150
```

### 4.8 Canonical JSON Example

```json
{
  "id": "b3d9f1a2-0001-4c3b-9f2d-000000000001",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "items": [
    {
      "food_item_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "quantity": 500,
      "unit": "g",
      "is_custom_entry": false,
      "custom_item_name": null,
      "added_at": "2026-03-24T08:00:00Z"
    },
    {
      "food_item_id": null,
      "quantity": 1,
      "unit": "units",
      "is_custom_entry": true,
      "custom_item_name": "Homemade hummus",
      "added_at": "2026-03-24T08:05:00Z"
    }
  ],
  "updated_at": "2026-03-24T08:05:00Z"
}
```

---

## 5. MealPlan Contract

### 5.1 Purpose
Represents one full day of planned meals for a user.
Contains 1–6 Meal objects, each with 1 or more MealItems.
All calorie and macro values are computed deterministically from FoodItem data.

### 5.2 MealPlan Structure

| Field            | Type          | Required | Constraints                                             |
|------------------|---------------|----------|---------------------------------------------------------|
| `id`             | UUID          | YES      | Auto-generated.                                         |
| `user_id`        | UUID          | YES      | References User.id.                                     |
| `date`           | date          | YES      | ISO 8601 (YYYY-MM-DD). One plan per user per date.      |
| `calorie_target` | integer       | YES      | 800–6000. Sourced from NutritionProfile.calorie_target. |
| `meals`          | array[Meal]   | YES      | 1–6 meals.                                              |
| `totals`         | MacroTotals   | NO       | Computed from all meals. Never stored as a free value.  |
| `calorie_gap`    | float         | NO       | `calorie_target − totals.calories`. Can be negative.    |
| `status`         | enum          | NO       | `"draft"` \| `"confirmed"`. Default: `"draft"`.         |
| `created_at`     | datetime      | NO       | ISO 8601. Immutable after creation.                     |
| `updated_at`     | datetime      | NO       | ISO 8601. Updated on status change or meal edit.        |

### 5.3 Meal Structure

| Field       | Type          | Required | Constraints                                              |
|-------------|---------------|----------|----------------------------------------------------------|
| `meal_id`   | UUID          | YES      | Auto-generated.                                          |
| `meal_type` | enum          | YES      | `"breakfast"` \| `"lunch"` \| `"dinner"` \| `"snack"`.  |
| `items`     | array[MealItem] | YES    | At least 1 item.                                         |
| `totals`    | MacroTotals   | NO       | Computed from items. Never stored as a free value.       |
| `name`      | string\|null  | NO       | Max 100 chars. Set by AI layer only (cosmetic).          |

**MealType rules:**
- Each `meal_type` value may appear **at most once** per MealPlan.
- Order within the `meals` array: breakfast → lunch → dinner → snack.

### 5.4 MealItem Structure

| Field          | Type   | Required | Constraints                                                        |
|----------------|--------|----------|--------------------------------------------------------------------|
| `food_item_id` | UUID   | YES      | References FoodItem.id. Must exist in food DB.                     |
| `quantity_g`   | float  | YES      | ≥ 1g.                                                              |
| `calories`     | float  | NO       | Computed only. Formula: `(calories_per_100g / 100) * quantity_g`.  |
| `protein_g`    | float  | NO       | Computed only. Formula: `(protein_per_100g  / 100) * quantity_g`.  |
| `carbs_g`      | float  | NO       | Computed only. Formula: `(carbs_per_100g    / 100) * quantity_g`.  |
| `fat_g`        | float  | NO       | Computed only. Formula: `(fat_per_100g      / 100) * quantity_g`.  |

> **CRITICAL:** `calories`, `protein_g`, `carbs_g`, and `fat_g` in MealItem
> are always computed via `NutritionEngine.compute_item_macros()`.
> They must never be set manually or by the AI layer.

### 5.5 MacroTotals Structure

Used at both the `Meal` level and the `MealPlan` level.

| Field      | Type  | Required | Constraints     |
|------------|-------|----------|-----------------|
| `calories` | float | YES      | ≥ 0             |
| `protein_g`| float | YES      | ≥ 0             |
| `carbs_g`  | float | YES      | ≥ 0             |
| `fat_g`    | float | YES      | ≥ 0             |

**Aggregation rule:**
```
Meal.totals     = SUM of all MealItem macro values within that Meal
MealPlan.totals = SUM of all Meal.totals within the MealPlan
calorie_gap     = MealPlan.calorie_target − MealPlan.totals.calories
```

### 5.6 Status Lifecycle

```
draft ──── (user confirms) ──→ confirmed
  │
  └── (user edits meal)  ──→ draft  (stays draft)
```

- Status transitions from `draft` → `confirmed` trigger inventory deduction (Agent 4).
- No reverse transition from `confirmed` to `draft` in MVP 1.

### 5.7 Validation Rules

```
MealPlan:
  id             → required, UUID v4
  user_id        → required, UUID v4, must reference valid User
  date           → required, ISO 8601 date, unique per user
  calorie_target → required, 800 ≤ value ≤ 6000
  meals          → required, 1 ≤ count ≤ 6
  status         → optional, default "draft"

Meal:
  meal_id        → required, UUID v4
  meal_type      → required, valid MealType enum value
  items          → required, count ≥ 1
  name           → optional, max 100 chars, AI-set only

MealItem:
  food_item_id   → required, must reference valid FoodItem
  quantity_g     → required, ≥ 1
  calories       → computed, set by Nutrition Engine only
  protein_g      → computed, set by Nutrition Engine only
  carbs_g        → computed, set by Nutrition Engine only
  fat_g          → computed, set by Nutrition Engine only
```

### 5.8 Canonical JSON Example

```json
{
  "id": "a1b2c3d4-0000-4000-8000-000000000001",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date": "2026-03-24",
  "calorie_target": 2302,
  "status": "draft",
  "meals": [
    {
      "meal_id": "f1e2d3c4-0000-4000-8000-000000000010",
      "meal_type": "breakfast",
      "name": null,
      "items": [
        {
          "food_item_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "quantity_g": 150,
          "calories": 247.5,
          "protein_g": 46.5,
          "carbs_g": 0.0,
          "fat_g": 5.4
        }
      ],
      "totals": {
        "calories": 247.5,
        "protein_g": 46.5,
        "carbs_g": 0.0,
        "fat_g": 5.4
      }
    }
  ],
  "totals": {
    "calories": 247.5,
    "protein_g": 46.5,
    "carbs_g": 0.0,
    "fat_g": 5.4
  },
  "calorie_gap": 2054.5,
  "created_at": "2026-03-24T09:00:00Z",
  "updated_at": "2026-03-24T09:00:00Z"
}
```

---

## 6. NutritionProfile Contract

### 6.1 Purpose
The output of Agent 2 (Nutrition Engine). A transient object — computed on demand,
not persisted as a primary record. Passed directly to Agent 5 (Meal Planning Engine).

### 6.2 Structure

| Field              | Type   | Required | Constraints               | Set By    |
|--------------------|--------|----------|---------------------------|-----------|
| `user_id`          | string | YES      | Valid UUID, matches User.id| Agent 2  |
| `bmr`              | float  | YES      | > 0                       | Agent 2   |
| `tdee`             | float  | YES      | ≥ bmr                     | Agent 2   |
| `calorie_target`   | int    | YES      | ≥ 800                     | Agent 2   |
| `protein_target_g` | float  | YES      | ≥ 0                       | Agent 2   |
| `carbs_target_g`   | float  | YES      | ≥ 0                       | Agent 2   |
| `fat_target_g`     | float  | YES      | ≥ 0                       | Agent 2   |

> No module other than Agent 2 may construct or mutate a NutritionProfile.
> Agent 5 receives it as read-only input.

### 6.3 Override Logic (Agent 2 must implement)

```
IF user.calorie_target_override IS NOT NULL:
    calorie_target = user.calorie_target_override
    (skip TDEE formula)
ELSE:
    calorie_target = TDEE + goal_delta
    (apply safety floor after)
```

---

## 7. Inter-Module Flow Contracts

### Data Flow Overview

```
[User Profile]
     |
     |  User object
     v
[Agent 2: Nutrition Engine]
     |
     |  NutritionProfile
     v
[Agent 5: Meal Planning Engine] <--- available_ids --- [Agent 4: Inventory Manager]
     |                                                          ^
     |  MealPlan (draft)                                        |
     v                                                   Inventory object
[Agent 6: AI Layer]
     |  (Meal.name only — no calorie/macro changes)
     v
[Agent 8: Mobile App]
     |
     | (on confirm)
     v
[Agent 4: Inventory Manager]  <--- deductions from confirmed MealPlan
```

---

### Contract F1 — User → Agent 2

**Input:** User object (required fields listed in Section 2.2)
**Output:** NutritionProfile (structure defined in Section 6.2)
**Rules:**
- Deterministic: same User input → same NutritionProfile output
- Must NOT call Agent 4 or Agent 5
- Must NOT call AI services

---

### Contract F2 — Agent 2 + Agent 4 → Agent 5

**Input:**
- `profile` — NutritionProfile from Agent 2
- `food_db` — Dict[UUID → FoodItem] from Agent 3
- `available_ids` — List[UUID] from Agent 4
- `plan_date` — ISO date

**Output:** MealPlan (structure defined in Section 5.2), status = `"draft"`

**Critical rule:** Every MealItem's macro fields must be set using
`NutritionEngine.compute_item_macros(food_item, quantity_g)` — never computed independently.

---

### Contract F3 — Agent 5 → Agent 6 (AI Layer)

**Input:**
```json
{
  "meal_plan_id": "uuid",
  "meals": [{ "meal_id": "uuid", "meal_type": "breakfast" }]
}
```

**Output:**
```json
{
  "meal_plan_id": "uuid",
  "meal_names": { "<meal_id>": "Display Name String" }
}
```

**Hard constraint:** Agent 6 returns meal display names **only**.
It must not modify quantities, macros, food_item_ids, or calorie_target.
Failure fallback: use `meal_type` enum value as display name.

---

### Contract F4 — Confirmed MealPlan → Agent 4 (Deduction)

**Trigger:** `MealPlan.status` changes to `"confirmed"`

**Input:**
```json
{
  "user_id": "uuid",
  "deductions": [
    { "food_item_id": "uuid", "quantity_used_g": 150.0 }
  ]
}
```

**Output:** Updated Inventory object.

**Rules:**
- Deduction only for items with `unit = "g"`
- Quantity floor = 0 (never negative)
- Unknown items (is_custom_entry = true) are never deducted

---

### Contract F5 — Agent 4 → Agent 5 (Availability)

**Input:** `{ "user_id": "uuid" }`

**Output:** `{ "available_ids": ["uuid-1", "uuid-2"] }`

**Rules:**
- Only items with `is_custom_entry = false` AND `quantity > 0` are included
- Agent 5 receives this list as read-only — it does not call Agent 4 directly

---

## 8. Frozen Structures

The following field sets are frozen by Agent 1. No downstream agent may
rename, retype, or remove these fields without a formal contract revision.

```
User:
  id, email, name, age, gender, height_cm, weight_kg,
  activity_level, goal, calorie_target_override,
  dietary_restrictions, subscription_tier

FoodItem:
  id, name, calories_per_100g, protein_per_100g,
  carbs_per_100g, fat_per_100g, category, is_custom

MealPlan:
  id, user_id, date, calorie_target, meals, status

Meal:
  meal_id, meal_type, items

MealItem:
  food_item_id, quantity_g, calories, protein_g, carbs_g, fat_g

MacroTotals:
  calories, protein_g, carbs_g, fat_g

Inventory:
  id, user_id, items

InventoryItem:
  food_item_id, quantity, unit, is_custom_entry, custom_item_name

NutritionProfile:
  user_id, bmr, tdee, calorie_target,
  protein_target_g, carbs_target_g, fat_target_g

AvailabilityReport:
  available_ids, missing_ids, shopping_list
```

---

## 9. Forbidden Cross-Module Calls

| From                    | Must NOT call                    | Reason                                         |
|-------------------------|----------------------------------|------------------------------------------------|
| Agent 2 (Nutrition)     | Agent 5 (Meal Planner)           | One-way data flow only                         |
| Agent 2 (Nutrition)     | Agent 4 (Inventory)              | Nutrition has no knowledge of stock            |
| Agent 2 (Nutrition)     | Any AI service                   | All calculations must be deterministic         |
| Agent 4 (Inventory)     | Agent 2 (Nutrition)              | Inventory has no calorie logic                 |
| Agent 4 (Inventory)     | Agent 5 (Meal Planner)           | Inventory does not know about plans            |
| Agent 5 (Meal Planner)  | NutritionEngine.calculate()      | Only compute_item_macros() is permitted        |
| Agent 5 (Meal Planner)  | Inventory (direct read/write)    | Must receive available_ids from Agent 4 only   |
| Agent 5 (Meal Planner)  | Any AI service                   | Meal generation must be deterministic          |
| Agent 6 (AI Layer)      | Agent 2 (Nutrition)              | AI never participates in calculations          |
| Agent 6 (AI Layer)      | Agent 4 (Inventory)              | AI has no access to user stock                 |
| Agent 6 (AI Layer)      | Food DB (write)                  | AI never modifies source data                  |
| Agent 7 (Payments)      | Agent 2, 4, or 5                 | Payments is fully isolated                     |
