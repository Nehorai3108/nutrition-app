"""
Queue Processor — iterates the unknown_queue and attempts to resolve each entry
via the Hebrew resolver + fallback agent pipeline.

Usage:
    python queue_processor.py          # process all pending items
    from queue_processor import process_unknown_queue
"""

from fallback_agent import search_with_fallback
from unknown_queue import get_pending_queue, update_status, queue_count


def process_unknown_queue() -> dict:
    """
    Attempt to resolve every pending item in the unknown queue.

    For each item:
      - Calls search_with_fallback (which now runs Hebrew resolution first).
      - Marks status as 'resolved' if found, 'failed' otherwise.

    Returns a summary dict:
        {
            "total":    int,   # items processed
            "resolved": int,
            "failed":   int,
            "details":  list[dict]
        }
    """
    pending = get_pending_queue()
    total = len(pending)

    if total == 0:
        print("[queue_processor] Queue is empty — nothing to process.")
        return {"total": 0, "resolved": 0, "failed": 0, "details": []}

    print(f"[queue_processor] Processing {total} pending item(s)...\n")

    resolved_count = 0
    failed_count = 0
    details = []

    for item in pending:
        query = item["query"]
        result = search_with_fallback(query)

        if result.get("found"):
            update_status(query, "resolved")
            resolved_count += 1
            status = "resolved"
            info = result.get("food_name", "?")
        else:
            update_status(query, "failed")
            failed_count += 1
            status = "failed"
            info = result.get("error", "unknown error")

        details.append({"query": query, "status": status, "info": info})
        print(f"  [{status:8s}] '{query}' -> {info}")

    print(f"\n[queue_processor] Done. resolved={resolved_count}  failed={failed_count}  total={total}")
    return {
        "total":    total,
        "resolved": resolved_count,
        "failed":   failed_count,
        "details":  details,
    }


if __name__ == "__main__":
    import sys
    import os

    # Allow running from repo root or from agents/
    sys.path.insert(0, os.path.dirname(__file__))

    summary = process_unknown_queue()

    remaining = queue_count() - summary["resolved"]
    print(f"\n── Summary ──────────────────────────────────")
    print(f"  Processed : {summary['total']}")
    print(f"  Resolved  : {summary['resolved']}")
    print(f"  Failed    : {summary['failed']}")
    print(f"  Still in queue (non-resolved): {summary['failed']}")
