"""
Simple test for Food Data Agent — Agent 1.
Runs two searches and prints results.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.food_data_agent import search_food


def _print_result(result: dict) -> None:
    sep = "-" * 48
    print(sep)
    print(f"  Query      : {result['query']}")
    if not result["found"]:
        print(f"  NOT FOUND  : {result['error']}")
        print(sep)
        return
    print(f"  Food name  : {result['food_name']}")
    print(f"  FDC ID     : {result['fdc_id']}")
    print(f"  Data type  : {result['data_type']}")
    print(f"  Serving    : {result['serving_size']} g" if result["serving_size"] else "  Serving    : N/A")
    print(f"  --- per 100g ---")
    print(f"  Calories   : {result['calories']} kcal")
    print(f"  Protein    : {result['protein']} g")
    print(f"  Carbs      : {result['carbs']} g")
    print(f"  Fat        : {result['fat']} g")
    print(f"  Fiber      : {result['fiber']} g")
    print(sep)


def main():
    queries = ["chicken breast", "\u05e2\u05d5\u05e3 \u05e6\u05dc\u05d5\u05d9"]  # עוף צלוי

    for q in queries:
        print(f"\nSearching: {q}")
        result = search_food(q)
        _print_result(result)


if __name__ == "__main__":
    main()
