"""Recipe image collection agent — fetches, stores, and tracks image approvals."""

from .image_fetcher import (
    fetch_candidates,
    load_pending,
    save_pending,
    approve,
    reject,
    run_batch,
    get_stats,
    PROJECT_ROOT,
    IMAGES_DIR,
)

__all__ = [
    "fetch_candidates",
    "load_pending",
    "save_pending",
    "approve",
    "reject",
    "run_batch",
    "get_stats",
    "PROJECT_ROOT",
    "IMAGES_DIR",
]
