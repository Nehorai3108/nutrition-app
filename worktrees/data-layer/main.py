"""
main.py - CLI entrypoint for the nutrition app autonomous cycle.

Usage:
    python main.py --cycle    Run the daily autonomous cycle (process queue + report + save log)
    python main.py --report   Print the most recent daily report
"""

import json
import os
import sys

# Ensure agents/ is importable from project root
_AGENTS_DIR = os.path.join(os.path.dirname(__file__), "agents")
sys.path.insert(0, _AGENTS_DIR)

_LOGS_DIR = os.path.join(_AGENTS_DIR, "logs")


# --- Commands -----------------------------------------------------------------

def cmd_cycle() -> None:
    from scheduler import run_daily_cycle

    result = run_daily_cycle()

    qr = result["queue_processing"]
    print("-- Queue Result ----------------------------------------------")
    print(f"  Processed : {qr['total']}")
    print(f"  Resolved  : {qr['resolved']}")
    print(f"  Failed    : {qr['failed']}")

    print("\n-- Report ----------------------------------------------------")
    _print_report(result["report"])


def cmd_report() -> None:
    if not os.path.isdir(_LOGS_DIR):
        print("No logs found. Run --cycle first.")
        return

    logs = sorted(
        [f for f in os.listdir(_LOGS_DIR) if f.startswith("daily_") and f.endswith(".json")],
        reverse=True,
    )
    if not logs:
        print("No logs found. Run --cycle first.")
        return

    log_path = os.path.join(_LOGS_DIR, logs[0])
    with open(log_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n-- Report: {data.get('date', '?')} ----------------------------")
    _print_report(data.get("report", {}))


# --- Helpers ------------------------------------------------------------------

def _print_report(report: dict) -> None:
    trend = report.get("trend")
    if trend is None:
        trend_str = "N/A (first run)"
    elif trend >= 0:
        trend_str = f"+{trend}%"
    else:
        trend_str = f"{trend}%"

    print(f"  Date           : {report.get('date', '?')}")
    print(f"  Cache size     : {report.get('cache_size', 0)} known foods")
    print(f"  Queue size     : {report.get('queue_size', 0)} unresolved")
    print(f"  Coverage rate  : {report.get('coverage_rate', 0):.1f}%")
    print(f"  Resolved today : {report.get('resolved_today', 0)}")
    print(f"  Trend vs prev  : {trend_str}")

    top_failed = report.get("top_failed", [])
    if top_failed:
        print(f"\n  Top failed foods ({len(top_failed)}):")
        for i, item in enumerate(top_failed, 1):
            print(f"    {i}. '{item['query']}' - {item['attempts']} attempt(s)")
    else:
        print("\n  Top failed foods: none")
    print()


# --- Entry point --------------------------------------------------------------

if __name__ == "__main__":
    if "--cycle" in sys.argv:
        cmd_cycle()
    elif "--report" in sys.argv:
        cmd_report()
    else:
        print("Usage: python main.py --cycle | --report")
        sys.exit(1)
