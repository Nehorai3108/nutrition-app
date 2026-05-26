"""
Food Data Agent — Operational agent for food catalog management.

Responsibility:
- Collect foods from defined sources (curated dataset + Open Food Facts API)
- Normalize names (Hebrew / English)
- Store per-100g nutrition values in the DB
- Maintain aliases in Hebrew and English
- Upsert without duplicates
- Log source, sync status, and failures
- Expose agent status summary

Input:  sync trigger (manual or scheduled)
Output: SyncResult dict, StatusSummary dict, food lookup results

Forbidden:
- Meal planning
- Nutrition target calculation
- Inventory management
- Recipe construction
"""

import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Optional

from db.database import NutritionDB
from pipeline.ingestion import run_ingestion_pipeline

# Layer 1 cache (agents/food_cache.db) — optional, graceful fallback if unavailable
try:
    _AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "agents")
    sys.path.insert(0, os.path.abspath(_AGENTS_DIR))
    from food_cache import get_cached as _layer1_get_cached  # type: ignore
except Exception:
    _layer1_get_cached = None  # type: ignore


class FoodDataAgent:
    """
    Operational agent that owns the food catalog lifecycle:
    sync → normalize → upsert → verify.
    """

    AGENT_ID = "agent_food_data"
    VERSION = "1.0.0"

    def __init__(self, db: Optional[NutritionDB] = None):
        self._db = db or NutritionDB()

    # ─── Public API ───────────────────────────────────────────────────

    def sync(self, use_api: bool = True) -> Dict:
        """
        Run a full sync cycle:
        1. Fetch from curated dataset (always)
        2. Fetch from Open Food Facts API (optional, graceful fallback)
        3. Normalize and upsert to DB
        4. Log run result

        Returns the sync result summary dict.
        """
        return run_ingestion_pipeline(db=self._db, use_api=use_api)

    def status(self) -> Dict:
        """
        Return a structured status summary for this agent.

        Fields:
          agent_id, version, is_ready, food_count, last_sync,
          total_failed, db_path, db_size_kb, recent_runs
        """
        food_count = self._db.get_food_count()
        last_sync = self._db.get_last_sync()
        recent_runs = self._db.get_recent_run_logs(limit=3)

        return {
            "agent_id": self.AGENT_ID,
            "version": self.VERSION,
            "is_ready": food_count > 0,
            "food_count": food_count,
            "last_sync": last_sync or "never",
            "total_failed_items": self._db.get_total_failed_items(),
            "db_path": self._db.db_path,
            "db_size_kb": self._db.get_db_size_kb(),
            "recent_runs": [
                {
                    "run_id": r["run_id"][:8] + "...",
                    "status": r["status"],
                    "started_at": r["started_at"],
                    "saved": r["items_saved"],
                    "updated": r["items_updated"],
                    "failed": r["items_failed"],
                }
                for r in recent_runs
            ],
        }

    def get_food(self, food_id: str) -> Optional[Dict]:
        """Return a single food by ID (per-100g values), or None."""
        return self._db.get_food_by_id(food_id)

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search foods by Hebrew or English name / alias.
        Checks Layer 1 cache (agents/food_cache.db) first to avoid redundant USDA calls.
        Returns list of matching food dicts (per-100g values).
        """
        if not query or not query.strip():
            return []

        # Pre-check Layer 1 cache before hitting NutritionDB / USDA
        if _layer1_get_cached is not None:
            cached = _layer1_get_cached(query)
            if cached:
                return [cached]

        normalized = _normalize_query(query)
        return self._db.search_foods(normalized, limit=limit)

    def all_foods(self, category: Optional[str] = None) -> List[Dict]:
        """Return all foods, optionally filtered by category."""
        return self._db.get_all_foods(category=category)

    def is_ready(self) -> bool:
        """True if the catalog has been populated (at least one food in DB)."""
        return self._db.get_food_count() > 0

    def print_status(self) -> None:
        """Print a formatted status report to stdout."""
        s = self.status()
        sep = "-" * 50
        print()
        print(sep)
        print("  FOOD DATA AGENT STATUS")
        print(sep)
        print(f"  Agent ID    : {s['agent_id']} v{s['version']}")
        print(f"  Ready       : {'YES' if s['is_ready'] else 'NO — run sync() first'}")
        print(f"  Foods in DB : {s['food_count']}")
        print(f"  Last sync   : {s['last_sync']}")
        print(f"  Failed total: {s['total_failed_items']}")
        print(f"  DB path     : {s['db_path']}")
        print(f"  DB size     : {s['db_size_kb']} KB")
        if s["recent_runs"]:
            print("  Recent runs :")
            for r in s["recent_runs"]:
                print(
                    f"    [{r['status'].upper():7}] {r['run_id']} "
                    f"saved={r['saved']} updated={r['updated']} failed={r['failed']}"
                )
        print(sep)
        print()


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _normalize_query(text: str) -> str:
    """Strip, lowercase, NFKD-normalize. Preserves Hebrew characters."""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    # Keep Hebrew (\u0590-\u05FF), Latin word chars, digits, spaces
    text = re.sub(r"[^\w\s\u0590-\u05FF]", "", text)
    return text
