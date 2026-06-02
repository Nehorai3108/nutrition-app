#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enrich_usda_nutrients.py
Fetches nutritional data for all USDA foods that have NULL calories,
using the /foods batch endpoint (200 at a time).
"""
import sys, json, sqlite3, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "storage" / "nutrition.db"
KEY     = "T8prNHixUyhB6WSZXVMCuEeslJ1HdZlvkc42rrsL"
URL     = f"https://api.nal.usda.gov/fdc/v1/foods?api_key={KEY}"

# Nutrient number → field name
NUTRIENT_MAP = {
    "208": "calories_kcal",
    "203": "protein_g",
    "205": "carbs_g",
    "204": "fat_g",
    "291": "fiber_g",
    "269": "sugar_g",
    "307": "sodium_mg",
}

def fetch_batch(fdc_ids: list[int]) -> dict:
    """POST /foods with list of fdcIds, return dict fdcId→nutrients."""
    body = json.dumps({"fdcIds": fdc_ids, "format": "abridged"}).encode()
    req  = urllib.request.Request(
        URL, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "BiteFit/1.0"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    foods = json.loads(resp.read().decode("utf-8"))
    result = {}
    for food in foods:
        fdc_id = food.get("fdcId")
        nuts   = {}
        for n in food.get("foodNutrients", []):
            num = str(n.get("number", ""))
            if num in NUTRIENT_MAP:
                nuts[NUTRIENT_MAP[num]] = n.get("amount")
        result[fdc_id] = nuts
    return result


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    # Get all USDA foods with missing calories
    rows = conn.execute(
        "SELECT food_id FROM foods WHERE source='usda' AND calories_kcal IS NULL"
    ).fetchall()

    fdc_pairs = []
    for (food_id,) in rows:
        try:
            fdc_id = int(food_id.replace("usda_", ""))
            fdc_pairs.append((food_id, fdc_id))
        except ValueError:
            pass

    total  = len(fdc_pairs)
    print(f"Found {total:,} USDA foods to enrich")

    batch_size = 20
    updated    = 0
    errors     = 0

    for i in range(0, total, batch_size):
        batch    = fdc_pairs[i:i + batch_size]
        food_ids = [p[0] for p in batch]
        fdc_ids  = [p[1] for p in batch]

        try:
            nut_data = fetch_batch(fdc_ids)
        except Exception as e:
            print(f"  Batch {i//batch_size+1} error: {e}")
            errors += 1
            time.sleep(2)
            continue

        for food_id, fdc_id in batch:
            nuts = nut_data.get(fdc_id, {})
            if not nuts:
                continue
            conn.execute("""
                UPDATE foods
                SET calories_kcal=?, protein_g=?, carbs_g=?, fat_g=?,
                    fiber_g=?, sugar_g=?, sodium_mg=?, updated_at=datetime('now')
                WHERE food_id=?
            """, (
                nuts.get("calories_kcal"),
                nuts.get("protein_g"),
                nuts.get("carbs_g"),
                nuts.get("fat_g"),
                nuts.get("fiber_g"),
                nuts.get("sugar_g"),
                nuts.get("sodium_mg"),
                food_id,
            ))
            updated += 1

        conn.commit()
        pct = (i + len(batch)) / total * 100
        print(f"  {i + len(batch):,}/{total:,} ({pct:.0f}%) | updated {updated:,}", end="\r")
        time.sleep(0.15)

    print(f"\nDone! Updated {updated:,} foods | {errors} batch errors")

    # Verify
    null_count = conn.execute(
        "SELECT COUNT(*) FROM foods WHERE source='usda' AND calories_kcal IS NULL"
    ).fetchone()[0]
    print(f"Still NULL: {null_count}")
    conn.close()


if __name__ == "__main__":
    main()
