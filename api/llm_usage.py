"""
Per-call LLM token + cost tracking.

One row per LLM API call (Groq today) so we can answer: "what does an active
user cost us per day/week, by feature?". Mirrors api/usage.py: Supabase table
`llm_usage` in prod, local SQLite for dev, and FAILS OPEN — a logging error must
never break the user-facing feature. Logs token counts + metadata only, never
message content.

Setup:
  DEMO_USER_IDS  comma-separated Supabase user ids → is_demo=True for those users
  DEVICE_LABEL   tag for the physical device generating the usage (default "unknown")
Read the results in the admin dashboard (pages_admin/5_llm_costs.py).
"""
import os
import json
import uuid
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "storage", "nutrition.db")

# ── Pricing: USD per 1,000,000 tokens. Edit here when rates change. ──────────
# Cached input is billed at 0.1× the input rate (Anthropic-style); harmless for
# providers without caching since cached_input_tokens stays 0.
PRICING: dict[str, dict] = {
    # Groq (pay-as-you-go) — approximate, editable.
    "llama-3.3-70b-versatile":               {"input": 0.59, "output": 0.79},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"input": 0.11, "output": 0.34},
    # Anthropic (kept for when/if we add Claude vision).
    "claude-haiku-4-5-20251001":             {"input": 1.00, "output": 5.00},
}
_DEFAULT_RATE = {"input": 0.0, "output": 0.0}


def _rates(model: str) -> dict:
    return PRICING.get(model, _DEFAULT_RATE)


def compute_cost(model: str, input_tokens: int, output_tokens: int,
                 cached_input_tokens: int = 0) -> float:
    r = _rates(model)
    billable_input = max(0, input_tokens - cached_input_tokens)
    cost = (billable_input / 1e6) * r["input"] + (output_tokens / 1e6) * r["output"]
    cost += (cached_input_tokens / 1e6) * r["input"] * 0.1
    return round(cost, 6)


# ── demo / device tagging ────────────────────────────────────────────────────
def _demo_user_ids() -> set:
    return {u.strip() for u in os.environ.get("DEMO_USER_IDS", "").split(",") if u.strip()}


def is_demo_user(user_id: str) -> bool:
    return bool(user_id) and user_id in _demo_user_ids()


def device_label(override: str | None = None) -> str:
    return (override or os.environ.get("DEVICE_LABEL") or "unknown").strip()[:60]


# ── token extraction (handles dict OR SDK object) ────────────────────────────
def _g(usage, *names, default=0):
    """Read the first present attribute/key from a usage dict or SDK object."""
    for n in names:
        if isinstance(usage, dict):
            if usage.get(n) is not None:
                return usage[n]
        elif getattr(usage, n, None) is not None:
            return getattr(usage, n)
    return default


def _extract_tokens(usage) -> dict:
    if not usage:
        return {"input": 0, "output": 0, "total": 0, "cached": 0}
    inp = int(_g(usage, "prompt_tokens", "input_tokens"))
    out = int(_g(usage, "completion_tokens", "output_tokens"))
    total = int(_g(usage, "total_tokens", default=inp + out)) or (inp + out)
    cached = int(_g(usage, "cache_read_input_tokens", "cached_input_tokens"))
    return {"input": inp, "output": out, "total": total, "cached": cached}


# ── storage ──────────────────────────────────────────────────────────────────
_CREATE = """
CREATE TABLE IF NOT EXISTS llm_usage (
    id                  TEXT PRIMARY KEY,
    created_at          TEXT NOT NULL,
    user_id             TEXT NOT NULL,
    is_demo             INTEGER NOT NULL DEFAULT 0,
    device_label        TEXT,
    provider            TEXT,
    model               TEXT,
    feature             TEXT,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    total_tokens        INTEGER DEFAULT 0,
    cached_input_tokens INTEGER DEFAULT 0,
    cost_usd            REAL DEFAULT 0,
    latency_ms          INTEGER,
    success             INTEGER DEFAULT 1,
    error               TEXT
)
"""


def _use_sb() -> bool:
    return bool(os.environ.get("SUPABASE_URL"))


def _sb():
    from nutrition_app.db.supabase_client import get_supabase
    return get_supabase()


def _conn():
    conn = sqlite3.connect(_DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE)
    return conn


def log_llm_usage(
    user_id: str,
    provider: str,
    model: str,
    feature: str,
    usage,
    latency_ms: int | None = None,
    success: bool = True,
    error: str | None = None,
    device_label_override: str | None = None,
) -> None:
    """Record one LLM call. FAILS OPEN — never raises to the caller."""
    try:
        uid = (user_id or "anon").strip() or "anon"
        tok = _extract_tokens(usage)
        cost = compute_cost(model, tok["input"], tok["output"], tok["cached"])
        row = {
            "id":                  uuid.uuid4().hex,
            "created_at":          datetime.now(timezone.utc).isoformat(),
            "user_id":             uid,
            "is_demo":             is_demo_user(uid),
            "device_label":        device_label(device_label_override),
            "provider":            provider,
            "model":               model,
            "feature":             feature,
            "input_tokens":        tok["input"],
            "output_tokens":       tok["output"],
            "total_tokens":        tok["total"],
            "cached_input_tokens": tok["cached"],
            "cost_usd":            cost,
            "latency_ms":          int(latency_ms) if latency_ms is not None else None,
            "success":             bool(success),
            "error":               (error or None) and str(error)[:300],
        }
        if _use_sb():
            _sb().table("llm_usage").insert(row).execute()
        else:
            r = dict(row)
            r["is_demo"] = 1 if r["is_demo"] else 0
            r["success"] = 1 if r["success"] else 0
            with closing(_conn()) as c:
                c.execute(
                    """INSERT INTO llm_usage
                       (id, created_at, user_id, is_demo, device_label, provider,
                        model, feature, input_tokens, output_tokens, total_tokens,
                        cached_input_tokens, cost_usd, latency_ms, success, error)
                       VALUES (:id,:created_at,:user_id,:is_demo,:device_label,:provider,
                        :model,:feature,:input_tokens,:output_tokens,:total_tokens,
                        :cached_input_tokens,:cost_usd,:latency_ms,:success,:error)""",
                    r,
                )
    except Exception:
        pass  # fail open — metering must never break a feature
