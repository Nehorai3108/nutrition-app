#!/usr/bin/env python3
"""
Initialize the relational schema on the database pointed to by
``DATABASE_URL`` (Supabase Postgres in production, SQLite in local dev).

Usage::

    # Supabase
    DATABASE_URL='postgresql+psycopg://USER:PASS@HOST:5432/postgres' \
        python scripts/init_supabase_schema.py

    # Local SQLite fallback (no env var)
    python scripts/init_supabase_schema.py

The script is idempotent: ``Base.metadata.create_all`` only creates tables
that do not already exist.

It does **not** apply Row Level Security policies — those must be added in
the Supabase SQL editor (see ``storage_audit/data_layer_audit.md``).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running this script with `python scripts/init_supabase_schema.py`
# from the repo root without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("init_supabase_schema")


def main() -> int:
    from nutrition_app.persistence import (  # noqa: WPS433 — script-level import
        Base,
        get_database_url,
        get_engine,
        init_db,
        is_postgres,
        is_sqlite,
    )

    url = get_database_url()
    redacted = url
    # Avoid printing credentials embedded in postgres://user:pass@host URLs.
    if "@" in redacted and "://" in redacted:
        scheme, rest = redacted.split("://", 1)
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        redacted = f"{scheme}://***@{rest}"
    logger.info("Target database: %s", redacted)
    logger.info("Dialect: %s", "postgres" if is_postgres(url) else ("sqlite" if is_sqlite(url) else "other"))

    engine = get_engine()
    init_db(engine)

    tables = sorted(Base.metadata.tables.keys())
    logger.info("Created/verified %d tables:", len(tables))
    for t in tables:
        logger.info("  - %s", t)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
