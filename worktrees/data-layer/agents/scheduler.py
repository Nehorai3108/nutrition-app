"""
Scheduler — orchestrates the daily autonomous cycle.

Steps:
    A. process_unknown_queue()   — attempt to resolve all pending items
    B. generate_daily_report()   — compute system statistics
    C. Save result to logs/daily_YYYY-MM-DD.json
"""

import json
import os
import sys
from datetime import datetime

# Allow importing sibling modules when called from project root
sys.path.insert(0, os.path.dirname(__file__))

from queue_processor import process_unknown_queue  # noqa: E402
from system_reporter import generate_daily_report  # noqa: E402

_LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")


def run_daily_cycle() -> dict:
    """
    Run the full daily autonomous cycle.

    Returns the complete cycle result dict (also written to logs/).
    """
    started_at = datetime.utcnow().isoformat()
    date_str = datetime.utcnow().date().isoformat()

    print(f"\n{'=' * 60}")
    print(f"  Daily Cycle - {date_str}")
    print(f"{'=' * 60}")

    # ── Step A: Process unknown queue ────────────────────────────────
    print("\n[Step A] Processing unknown queue...")
    queue_result = process_unknown_queue()

    # ── Step B: Generate daily report ────────────────────────────────
    print("\n[Step B] Generating daily report...")
    report = generate_daily_report()

    # ── Step C: Persist log ──────────────────────────────────────────
    os.makedirs(_LOGS_DIR, exist_ok=True)
    log_path = os.path.join(_LOGS_DIR, f"daily_{date_str}.json")

    cycle_result = {
        "date": date_str,
        "started_at": started_at,
        "finished_at": datetime.utcnow().isoformat(),
        "queue_processing": queue_result,
        "report": report,
    }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(cycle_result, f, ensure_ascii=False, indent=2)

    print(f"\n[Step C] Log saved: {log_path}")
    print(f"\n{'=' * 60}")
    print("  Cycle complete.")
    print(f"{'=' * 60}\n")

    return cycle_result
