#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_storage_agents.py
=========================
One-time migration from flat storage_agents/ layout to the multi-user
namespaced layout:

    storage_agents/users/{user_id}/plans/   <- was storage_agents/plans/
    storage_agents/users/{user_id}/...      <- flat per-user files

The script is IDEMPOTENT — safe to run multiple times.  It copies files
rather than moving them so the original flat structure remains intact
and can be removed manually after verifying the migration.

Usage:
    python scripts/migrate_storage_agents.py [--root PATH]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# ── Project root is one level above this script's directory ───────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate storage_agents/ to per-user layout")
    parser.add_argument(
        "--root",
        default=str(PROJECT_ROOT / "storage_agents"),
        help="Path to storage_agents/ root (default: <project>/storage_agents/)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: storage root does not exist: {root}")
        return 1

    moved_total = 0
    skipped_total = 0

    # ── Helper ────────────────────────────────────────────────────────────────

    def _copy(src: Path, dst: Path) -> bool:
        """Copy src -> dst, creating parent dirs. Returns True if actually copied."""
        if dst.exists():
            return False  # idempotent: already there
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True

    # ── 1. Per-user flat files ─────────────────────────────────────────────────
    #   storage_agents/{folder}/{user_id}.json  ->
    #   storage_agents/users/{user_id}/{dest_name}

    PER_USER_FLAT = {
        "profiles":        "profile.json",
        "inventories":     "inventory.json",
        "food_log":        "food_log.json",
        "daily_summaries": "daily_summaries.json",
        "water":           "water.json",
        "workouts":        "workouts.json",
        "weekly_plans":    "weekly_plan.json",
    }

    for folder_name, dest_name in PER_USER_FLAT.items():
        src_dir = root / folder_name
        if not src_dir.is_dir():
            continue
        for src_file in src_dir.glob("*.json"):
            user_id = src_file.stem
            dst = root / "users" / user_id / dest_name
            if _copy(src_file, dst):
                print(f"  moved  {folder_name}/{src_file.name}  ->  users/{user_id}/{dest_name}")
                moved_total += 1
            else:
                skipped_total += 1

    # ── 2. Plans: sort by user_id field inside each JSON ─────────────────────

    plans_src = root / "plans"
    if plans_src.is_dir():
        plan_files = list(plans_src.glob("*.json"))
        print(f"\nMigrating {len(plan_files)} plan files from plans/ ...")
        for plan_file in plan_files:
            try:
                with open(plan_file, encoding="utf-8") as fh:
                    plan = json.load(fh)
                user_id = plan.get("user_id") or "demo"
            except Exception:
                user_id = "demo"

            dst = root / "users" / user_id / "plans" / plan_file.name
            if _copy(plan_file, dst):
                moved_total += 1
            else:
                skipped_total += 1

        # Summary by user
        by_user: dict[str, int] = {}
        for plan_file in plans_src.glob("*.json"):
            try:
                with open(plan_file, encoding="utf-8") as fh:
                    uid = json.load(fh).get("user_id", "demo")
            except Exception:
                uid = "demo"
            by_user[uid] = by_user.get(uid, 0) + 1
        for uid, count in sorted(by_user.items()):
            print(f"    users/{uid}/plans/  <- {count} files")
    else:
        print("  (no legacy plans/ directory found — skipping)")

    # ── 3. Summary ────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"Migration complete.")
    print(f"  Files copied:  {moved_total}")
    print(f"  Already there: {skipped_total}")
    print()
    print("Next steps:")
    print("  1. Verify destination files in storage_agents/users/")
    print("  2. Update any remaining code paths if needed.")
    print("  3. Remove old flat directories once code is tested:")
    for folder_name in list(PER_USER_FLAT.keys()) + ["plans"]:
        print(f"       storage_agents/{folder_name}/")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
