#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Expansion Runner
======================
Called once per day (via scheduled task or cron).
Collects new foods & recipes, runs the agent loop, tracks growth.

Usage:
  python run_daily_expansion.py
"""

import io
import os
import sys
from datetime import datetime

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nutrition_app.autonomy.expansion.expansion_engine import ExpansionEngine

STORAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage_agents")
WIDTH = 62


def main() -> int:
    print("=" * WIDTH)
    print(f"  הרחבה יומית — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * WIDTH)

    engine = ExpansionEngine(storage_dir=STORAGE)
    report = engine.run_daily_cycle()

    print()
    print(f"  מזונות חדשים:    +{report.foods_added} (סה\"כ: {report.catalog_size})")
    print(f"  מתכונים חדשים:   +{report.recipes_added} (סה\"כ: {report.recipes_count})")
    print(f"  תבניות חדשות:    +{report.templates_added}")
    print(f"  ציון בריאות:      {report.health_score}/100")

    if report.milestones_reached:
        print()
        for m in report.milestones_reached:
            print(f"  ** {m}")

    print()
    print("=" * WIDTH)
    if report.health_score >= 70:
        print("  הרחבה הושלמה בהצלחה")
    else:
        print("  הרחבה הושלמה (ציון בריאות נמוך)")
    print("=" * WIDTH)

    return 0 if report.health_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
