"""
Database engine / session factory.

Reads ``DATABASE_URL`` from the environment (loading a local ``.env`` if
present). Falls back to a local SQLite file at ``storage/nutrition.db`` with a
logged warning if ``DATABASE_URL`` is unset — this keeps local development
friction-free while letting deployments point at Supabase Postgres.

The ``connect_args`` and pool settings are picked appropriate to the dialect:
SQLite needs ``check_same_thread=False`` for Streamlit's multi-thread use;
Postgres uses a pre-ping/pool-recycle pattern that's friendly to managed
databases (Supabase pooler).
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)


# Canonical default user_id used in local dev / when no user is logged in.
# Matches the convention in storage_audit/data_layer_audit.md section 3d.
DEFAULT_USER_ID = "demo"


_SQLITE_DEFAULT_PATH = "storage/nutrition.db"


def _load_dotenv_if_present() -> None:
    """Best-effort load of a project-level .env file.

    Uses python-dotenv when available; otherwise does nothing. The fallback is
    intentional — we don't want to fail if python-dotenv isn't installed in a
    given environment (e.g., minimal CI).
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:  # pragma: no cover — dotenv is optional
        return
    # Walk up from this file to find a .env at the repo root.
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            break


def get_database_url() -> str:
    """Resolve the database URL.

    Order of resolution:
      1. ``DATABASE_URL`` env var (loaded from .env if present).
      2. Fallback to ``sqlite:///<repo>/storage/nutrition.db`` with a warning.
    """
    _load_dotenv_if_present()
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url

    # Resolve repo-root-relative SQLite path so the same fallback works
    # regardless of the process cwd.
    repo_root = Path(__file__).resolve().parents[2]
    sqlite_path = repo_root / _SQLITE_DEFAULT_PATH
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    fallback = f"sqlite:///{sqlite_path.as_posix()}"
    logger.warning(
        "DATABASE_URL is not set; falling back to local SQLite at %s",
        fallback,
    )
    return fallback


def is_sqlite(url: Optional[str] = None) -> bool:
    return (url or get_database_url()).startswith("sqlite")


def is_postgres(url: Optional[str] = None) -> bool:
    u = url or get_database_url()
    return u.startswith("postgresql") or u.startswith("postgres")


def create_db_engine(url: Optional[str] = None, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine with dialect-appropriate options."""
    db_url = url or get_database_url()

    if db_url.startswith("sqlite"):
        # check_same_thread=False is required because Streamlit reuses
        # connections across threads. SQLite is single-writer either way.
        return create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False},
            future=True,
        )

    # Assume Postgres-compatible (Supabase). pool_pre_ping + recycle plays
    # nicely with managed Postgres connection poolers.
    return create_engine(
        db_url,
        echo=echo,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


class Base(DeclarativeBase):
    """Declarative base for all ORM models in this package."""


# Lazy singletons — initialized on first access so importing this module never
# triggers a connection.
_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _SessionFactory


def SessionLocal() -> Session:  # noqa: N802 — kept PascalCase by convention
    """Return a new ORM Session bound to the configured engine."""
    return _get_session_factory()()


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager that yields a session and commits/rolls back on exit."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Optional[Engine] = None) -> None:
    """Create all tables on the given (or default) engine."""
    # Import models for side-effects (table registration).
    from . import models  # noqa: F401

    Base.metadata.create_all(engine or get_engine())


def reset_engine_for_tests() -> None:
    """Forget cached engine / session factory.

    Test fixtures that override ``DATABASE_URL`` after import call this to
    force re-resolution. Production code never needs this.
    """
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None
