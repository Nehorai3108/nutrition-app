"""
Test: cache + fallback layer
  - "chicken breast" → should hit USDA on first call, then return from cache on second
  - "עוף צלוי"       → expected to fail all sources and land in unknown_queue
  - Print cache count and queue count at the end
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fallback_agent import search_with_fallback
from food_cache import cache_count
from unknown_queue import queue_count


def _print_result(label: str, result: dict) -> None:
    print(f"\n{'─'*60}")
    print(f"  Query  : {label}")
    print(f"  Found  : {result['found']}")
    print(f"  Source : {result.get('source')}")
    if result["found"]:
        print(f"  Name   : {result['food_name']}")
        print(f"  Cal    : {result['calories']} kcal/100g")
        print(f"  Protein: {result['protein']} g")
        print(f"  Carbs  : {result['carbs']} g")
        print(f"  Fat    : {result['fat']} g")
        print(f"  Fiber  : {result['fiber']} g")
    else:
        print(f"  Error  : {result['error']}")


# ── Test 1: chicken breast ────────────────────────────────────────────────────
print("\n=== Test 1: first call (expected: usda or off) ===")
r1 = search_with_fallback("chicken breast")
_print_result("chicken breast", r1)

print("\n=== Test 1b: second call (expected: cache) ===")
r1b = search_with_fallback("chicken breast")
_print_result("chicken breast", r1b)
assert r1b.get("from_cache"), "Expected cache hit on second call!"

# ── Test 2: Hebrew query ──────────────────────────────────────────────────────
print("\n=== Test 2: 'עוף צלוי' (expected: unknown_queue) ===")
r2 = search_with_fallback("עוף צלוי")
_print_result("עוף צלוי", r2)
assert r2["source"] == "unknown", "Expected 'unknown' source for Hebrew query"

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  Cache entries : {cache_count()}")
print(f"  Unknown queue : {queue_count()}")
print(f"{'='*60}\n")
