"""
Food ingestion pipeline — fetch → upsert → log.
"""

import uuid
from datetime import datetime, timezone
from typing import List

from db.database import NutritionDB
from pipeline.food_source import fetch_curated, fetch_from_open_food_facts


def run_ingestion_pipeline(db: NutritionDB = None, use_api: bool = True) -> dict:
    """
    Run the full food ingestion pipeline.

    - Fetches from curated dataset (always) + Open Food Facts API (optional).
    - Upserts all foods into SQLite (insert new, update existing).
    - Logs the run with start time, end time, and item counts.
    - Returns a summary dict.
    """
    if db is None:
        db = NutritionDB()

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    print(f"\n[{_ts()}] Pipeline started  (run={run_id[:8]}...)")
    db.create_run_log(run_id, started_at)

    errors: List[str] = []
    items_saved = 0
    items_updated = 0
    items_failed = 0

    # ── 1. Fetch ──────────────────────────────────────────────────────────────
    print(f"[{_ts()}] Loading curated dataset...")
    foods = fetch_curated()
    print(f"[{_ts()}] Curated: {len(foods)} foods")

    if use_api:
        print(f"[{_ts()}] Fetching from Open Food Facts API (timeout=5s)...")
        try:
            api_foods = fetch_from_open_food_facts()
            if api_foods:
                print(f"[{_ts()}] API:     {len(api_foods)} additional foods")
                foods.extend(api_foods)
            else:
                print(f"[{_ts()}] API:     0 foods (no results or offline)")
        except Exception as exc:
            msg = f"API fetch skipped: {exc}"
            print(f"[{_ts()}] WARNING  {msg}")
            errors.append(msg)

    items_fetched = len(foods)
    print(f"[{_ts()}] Total fetched: {items_fetched}")

    # ── 2. Upsert ─────────────────────────────────────────────────────────────
    print(f"[{_ts()}] Writing to database...")
    for food in foods:
        try:
            result = db.upsert_food(food)
            if result == "inserted":
                items_saved += 1
            else:
                items_updated += 1
        except Exception as exc:
            items_failed += 1
            errors.append(f"Failed {food.get('food_id', '?')}: {exc}")

    # ── 3. Finalize ───────────────────────────────────────────────────────────
    ended_at = datetime.now(timezone.utc).isoformat()
    status = "failed" if items_failed > 0 and (items_saved + items_updated) == 0 else "success"

    db.update_run_log(
        run_id,
        ended_at=ended_at,
        items_fetched=items_fetched,
        items_saved=items_saved,
        items_updated=items_updated,
        items_failed=items_failed,
        errors=errors,
        status=status,
    )

    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "items_fetched": items_fetched,
        "items_saved": items_saved,
        "items_updated": items_updated,
        "items_failed": items_failed,
        "errors": errors,
        "status": status,
    }

    _print_run_summary(summary)
    _print_db_status(db)

    return summary


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


_SEP = "-" * 60


def _print_run_summary(s: dict) -> None:
    print()
    print(_SEP)
    print("  RUN SUMMARY")
    print(_SEP)
    print(f"  Status        : {s['status'].upper()}")
    print(f"  Run ID        : {s['run_id'][:8]}...")
    print(f"  Started       : {s['started_at']}")
    print(f"  Ended         : {s['ended_at']}")
    print(f"  Fetched       : {s['items_fetched']}")
    print(f"  Saved (new)   : {s['items_saved']}")
    print(f"  Updated       : {s['items_updated']}")
    print(f"  Failed        : {s['items_failed']}")
    if s["errors"]:
        print("  Errors        :")
        for err in s["errors"][:5]:
            print(f"    - {err}")
        if len(s["errors"]) > 5:
            print(f"    ... and {len(s['errors']) - 5} more")
    print(_SEP)


def _print_db_status(db: NutritionDB) -> None:
    print()
    print("  DATABASE STATUS")
    print(_SEP)
    print(f"  Path          : {db.db_path}")
    print(f"  Size          : {db.get_db_size_kb()} KB")
    print(f"  Total foods   : {db.get_food_count()}")
    print(f"  Last sync     : {db.get_last_sync() or 'never'}")
    print(f"  Total failed  : {db.get_total_failed_items()}")
    print(_SEP)
    print()
