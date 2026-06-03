"""
Plan variety fixer (Agent 4/5 utility — Agent 2 builder task 2026-05-27_151228_sel).

For each of the 7 most recently modified plan json files in storage_agents/plans/,
join items against the food catalog (nutrition_app/data/foods_extended.json) to
get categories, compute per-day share of items per category, and if any of the
tracked categories (PROTEIN, GRAIN, VEG, FRUIT, DAIRY) exceeds 60 percent of the
day's item count, swap exactly one item: replace one item from the
over-represented category with a same-meal-context item from an under-represented
category, preserving total daily kcal within +/- 5 percent.

Outputs: <original>_variety_fix.json sibling files (does not overwrite the
original). A 'variety_fix' provenance block is added to each output file with
the original_item food_id, replacement food_id, and per-category share before
and after.

This script is idempotent: if no plan violates the rule, no files are written.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Category mapping: rule names in acceptance criteria -> catalog 'category' values
TRACKED_CATS = {
    "PROTEIN": "protein",
    "GRAIN": "grain",
    "VEG": "vegetable",
    "FRUIT": "fruit",
    "DAIRY": "dairy",
}
CATALOG_TO_RULE = {v: k for k, v in TRACKED_CATS.items()}

THRESHOLD = 0.60
KCAL_TOLERANCE = 0.05  # +/- 5%


def load_catalog(catalog_path: Path) -> dict:
    with catalog_path.open("r", encoding="utf-8") as f:
        items = json.load(f)
    return {it["food_id"]: it for it in items}


def newest_plan_files(plans_dir: Path, n: int = 7) -> list[Path]:
    """Return the n newest plan .json files (excluding variety_fix outputs)."""
    candidates = [
        p for p in plans_dir.iterdir()
        if p.is_file()
        and p.suffix == ".json"
        and not p.name.endswith("_variety_fix.json")
    ]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[:n]


def compute_category_shares(plan: dict, catalog: dict) -> tuple[dict, int, list[tuple[int, int, str, str]]]:
    """
    Return:
      shares: dict[rule_name] -> share (0..1) over the day's TOTAL ITEMS in tracked cats only
              (the rule says: "no single food category ... should account for more than 60% of
              items across the day"; we interpret 'items across the day' as the total count of
              items in the plan, not just tracked-cat items)
      total_items: total items in plan
      item_index: list of (meal_idx, item_idx, food_id, rule_category_or_None)
    """
    rule_counts = {k: 0 for k in TRACKED_CATS}
    total_items = 0
    item_index: list[tuple[int, int, str, str | None]] = []
    for mi, meal in enumerate(plan.get("meals", [])):
        for ii, item in enumerate(meal.get("items", [])):
            total_items += 1
            fid = item.get("food_id")
            cat = (catalog.get(fid) or {}).get("category")
            rule_cat = CATALOG_TO_RULE.get(cat)
            item_index.append((mi, ii, fid, rule_cat))
            if rule_cat:
                rule_counts[rule_cat] += 1
    shares = {k: (c / total_items if total_items else 0.0) for k, c in rule_counts.items()}
    return shares, total_items, item_index


def find_violation(shares: dict) -> str | None:
    """Return the rule_name of the over-60% category (highest share above threshold), or None."""
    over = [(k, v) for k, v in shares.items() if v > THRESHOLD]
    if not over:
        return None
    over.sort(key=lambda kv: -kv[1])
    return over[0][0]


def pick_replacement(
    plan: dict,
    catalog: dict,
    over_rule: str,
    item_index: list,
) -> tuple[int, int, str, dict] | None:
    """
    Pick exactly one item to swap.

    Strategy:
      1. Among items belonging to the over-represented rule category, pick the one whose
         removal+replacement keeps daily kcal closest to original. We pick the item in
         the most-populated meal of that category (so the meal stays balanced).
      2. Replacement is a catalog item from an under-represented rule category (smallest
         current share among the 5 tracked) whose kcal at same quantity_g (using
         nutrition_per_100g) yields a total daily kcal within +/- 5% of the original.
      3. Same-meal-context: keep the same meal_type. The replacement is inserted in the
         same meal position with the same quantity_g, but with new nutrition recomputed
         from the catalog.

    Returns (meal_idx, item_idx, replacement_food_id, new_item_dict) or None if no
    feasible swap exists.
    """
    # Daily kcal pre-swap (use plan totals if present, else compute)
    daily_kcal = float(plan.get("totals", {}).get("calories_kcal", 0.0)) or sum(
        float(it.get("calories_kcal", 0.0))
        for meal in plan.get("meals", [])
        for it in meal.get("items", [])
    )
    if daily_kcal <= 0:
        return None

    # All items in the over-represented category
    over_items = [(mi, ii, fid) for (mi, ii, fid, rc) in item_index if rc == over_rule]
    if not over_items:
        return None

    # Find under-represented tracked categories (those with the smallest current share)
    # Recompute shares to get current state
    rule_counts = {k: 0 for k in TRACKED_CATS}
    total_items = 0
    for (mi, ii, fid, rc) in item_index:
        total_items += 1
        if rc:
            rule_counts[rc] += 1
    # Sort tracked rules by current share ascending; exclude over_rule itself
    under_rules = sorted(
        [(k, c / total_items if total_items else 0.0) for k, c in rule_counts.items() if k != over_rule],
        key=lambda kv: kv[1],
    )

    # Build candidate replacement food_ids per under-rule from catalog
    def catalog_candidates_for_rule(rule_name: str) -> list[dict]:
        cat_name = TRACKED_CATS[rule_name]
        return [it for it in catalog.values() if it.get("category") == cat_name]

    # For each over-category item, try to find a replacement that keeps kcal in tolerance.
    # Prefer the item from a meal that has the highest count of over-category items
    # (least disruption to that meal's balance).
    meal_over_counts: dict[int, int] = {}
    for (mi, ii, fid) in over_items:
        meal_over_counts[mi] = meal_over_counts.get(mi, 0) + 1
    over_items_sorted = sorted(
        over_items,
        key=lambda t: (-meal_over_counts[t[0]], t[0], t[1]),
    )

    for (mi, ii, fid) in over_items_sorted:
        original_item = plan["meals"][mi]["items"][ii]
        original_kcal = float(original_item.get("calories_kcal", 0.0))
        qty_g = float(original_item.get("quantity_g", 0.0))
        if qty_g <= 0:
            continue
        # Try each under-rule from least-represented upward
        for (rule_name, _share) in under_rules:
            for cand in catalog_candidates_for_rule(rule_name):
                npg = cand.get("nutrition_per_100g") or {}
                kcal_per_100 = float(npg.get("calories_kcal", 0.0))
                if kcal_per_100 <= 0:
                    continue
                new_item_kcal = round(kcal_per_100 * qty_g / 100.0, 1)
                # Resulting daily kcal
                new_daily = daily_kcal - original_kcal + new_item_kcal
                deviation = abs(new_daily - daily_kcal) / daily_kcal
                if deviation <= KCAL_TOLERANCE:
                    # Build replacement item, keep same quantity_g
                    new_item = {
                        "food_id": cand["food_id"],
                        "food_name": cand.get("name_he") or cand.get("name_en") or cand["food_id"],
                        "quantity_g": qty_g,
                        "calories_kcal": new_item_kcal,
                        "protein_g": round(float(npg.get("protein_g", 0.0)) * qty_g / 100.0, 1),
                        "carbs_g": round(float(npg.get("carbs_g", 0.0)) * qty_g / 100.0, 1),
                        "fat_g": round(float(npg.get("fat_g", 0.0)) * qty_g / 100.0, 1),
                        "from_inventory": False,
                        "inventory_item_id": None,
                    }
                    return mi, ii, cand["food_id"], new_item
    return None


def recompute_meal_and_plan_totals(plan: dict) -> None:
    """Recompute per-meal totals and plan-level totals after a swap, in-place."""
    plan_totals = {"calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for meal in plan.get("meals", []):
        mt = {"calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for it in meal.get("items", []):
            for k in mt:
                mt[k] += float(it.get(k, 0.0))
        # Round to 1 decimal
        meal["totals"] = {k: round(v, 1) for k, v in mt.items()}
        for k in plan_totals:
            plan_totals[k] += mt[k]
    plan["totals"] = {k: round(v, 1) for k, v in plan_totals.items()}
    # Recompute calorie_deviation_pct if target present
    target = plan.get("target_calories_kcal")
    if target:
        dev = (plan["totals"]["calories_kcal"] - target) / target * 100.0
        plan["calorie_deviation_pct"] = round(dev, 1)


def process_plan_file(plan_path: Path, catalog: dict) -> dict:
    """Process a single plan file. Returns a dict with status info."""
    with plan_path.open("r", encoding="utf-8") as f:
        plan = json.load(f)
    shares_before, total_items, item_index = compute_category_shares(plan, catalog)
    over_rule = find_violation(shares_before)
    info = {
        "plan_file": plan_path.name,
        "total_items": total_items,
        "shares_before": {k: round(v, 4) for k, v in shares_before.items()},
        "violation": over_rule,
        "modified": False,
    }
    if not over_rule:
        return info

    pick = pick_replacement(plan, catalog, over_rule, item_index)
    if not pick:
        info["error"] = (
            f"No feasible swap found for {over_rule} (no replacement keeps daily kcal in +/- 5%)"
        )
        return info
    meal_idx, item_idx, replacement_fid, new_item = pick
    original_item = dict(plan["meals"][meal_idx]["items"][item_idx])
    # Apply swap
    plan["meals"][meal_idx]["items"][item_idx] = new_item
    # Recompute totals
    daily_kcal_before = float(plan.get("totals", {}).get("calories_kcal", 0.0))
    recompute_meal_and_plan_totals(plan)
    daily_kcal_after = float(plan["totals"]["calories_kcal"])
    # Recompute shares after
    shares_after, _, _ = compute_category_shares(plan, catalog)
    # Provenance
    plan["variety_fix"] = {
        "original_item": {
            "meal_idx": meal_idx,
            "item_idx": item_idx,
            "food_id": original_item.get("food_id"),
            "food_name": original_item.get("food_name"),
            "calories_kcal": original_item.get("calories_kcal"),
            "category_rule": over_rule,
        },
        "replacement_item": {
            "food_id": replacement_fid,
            "food_name": new_item["food_name"],
            "calories_kcal": new_item["calories_kcal"],
            "category_rule": CATALOG_TO_RULE.get(
                (catalog.get(replacement_fid) or {}).get("category")
            ),
        },
        "category_shares_before": {k: round(v, 4) for k, v in shares_before.items()},
        "category_shares_after": {k: round(v, 4) for k, v in shares_after.items()},
        "daily_kcal_before": round(daily_kcal_before, 1),
        "daily_kcal_after": round(daily_kcal_after, 1),
        "kcal_deviation_pct": (
            round((daily_kcal_after - daily_kcal_before) / daily_kcal_before * 100.0, 2)
            if daily_kcal_before
            else 0.0
        ),
        "rule_threshold": THRESHOLD,
    }
    # Write sibling file
    out_path = plan_path.with_name(plan_path.stem + "_variety_fix.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    info.update({
        "modified": True,
        "output_file": out_path.name,
        "shares_after": {k: round(v, 4) for k, v in shares_after.items()},
        "swap": {
            "from": original_item.get("food_id"),
            "to": replacement_fid,
            "meal_idx": meal_idx,
            "item_idx": item_idx,
        },
    })
    return info


def main() -> int:
    here = Path(__file__).resolve()
    project_root = here.parents[2]  # nutrition_app/scripts/.. -> nutrition_app/.. -> project root
    plans_dir = project_root / "storage_agents" / "plans"
    catalog_path = project_root / "nutrition_app" / "data" / "foods_extended.json"
    if not plans_dir.is_dir():
        print(f"ERROR: plans dir not found: {plans_dir}", file=sys.stderr)
        return 2
    if not catalog_path.is_file():
        print(f"ERROR: food catalog not found: {catalog_path}", file=sys.stderr)
        return 2
    catalog = load_catalog(catalog_path)
    plan_files = newest_plan_files(plans_dir, n=7)
    print(f"Processing {len(plan_files)} newest plan files:")
    summary = []
    for p in plan_files:
        info = process_plan_file(p, catalog)
        summary.append(info)
        status = "MODIFIED" if info.get("modified") else ("VIOLATION_NO_SWAP" if info.get("error") else "OK")
        print(f"  [{status}] {info['plan_file']} shares_before={info['shares_before']} violation={info.get('violation')}")
        if info.get("modified"):
            print(f"    -> wrote {info['output_file']}; swap {info['swap']['from']} -> {info['swap']['to']}")
        if info.get("error"):
            print(f"    -> {info['error']}")
    # Print summary JSON to stdout for easy parsing
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
