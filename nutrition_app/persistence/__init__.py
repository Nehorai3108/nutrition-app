"""
Persistence layer — SQLAlchemy engine, session factory, and ORM models.

This package introduces the relational schema for the multi-user refactor.
It coexists with the existing JSON-file repositories (under
``nutrition_app/repositories/``). The JSON repos remain authoritative for the
current Streamlit UI; the SQLAlchemy models are the destination schema for the
Supabase Postgres migration (and a SQLite local-dev fallback).

Two storage systems exist in this codebase:
  * ``nutrition_app/repositories/`` — flat-JSON repositories (per-user files
    where applicable). Used by the UI today.
  * ``nutrition_app/user_manager.py`` — second, parallel per-user JSON store.
    Left untouched (see data_layer_audit.md migration notes).

The SQLAlchemy layer in this package is additive: it does not displace the
JSON repos. It is wired in via ``DATABASE_URL`` (Supabase Postgres) with a
SQLite fallback (``sqlite:///storage/nutrition.db``).
"""

from .database import (
    Base,
    DEFAULT_USER_ID,
    SessionLocal,
    create_db_engine,
    get_database_url,
    get_engine,
    get_session,
    init_db,
    is_postgres,
    is_sqlite,
)
from . import models  # noqa: F401  (registers ORM tables on Base.metadata)

__all__ = [
    "Base",
    "DEFAULT_USER_ID",
    "SessionLocal",
    "create_db_engine",
    "get_database_url",
    "get_engine",
    "get_session",
    "init_db",
    "is_postgres",
    "is_sqlite",
    "models",
]
