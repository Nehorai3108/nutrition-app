"""
Shared test fixtures and configuration.

The fixtures here support the multi-user refactor:

* ``test_user_id`` -- canonical id used in repository fixtures.
* ``other_user_id`` -- second id used in isolation tests (one user must not
  read another user's rows).
* ``tmp_storage_dir`` -- fresh storage directory per test.
* ``sqlite_engine`` / ``db_session`` -- in-memory SQLite engine + session for
  ORM-level tests, so we don't need a real Postgres for the unit suite.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def test_user_id() -> str:
    """Canonical user_id used across repository fixtures."""
    return "test_user_1"


@pytest.fixture
def other_user_id() -> str:
    """Second user_id for isolation tests."""
    return "test_user_2"


@pytest.fixture
def tmp_storage_dir(tmp_path):
    """A fresh storage directory for a single test."""
    return str(tmp_path)


@pytest.fixture
def sqlite_engine(monkeypatch):
    """In-memory SQLite engine for ORM-level tests.

    Sets DATABASE_URL to a per-test in-memory database and resets the
    module-level cached engine so get_engine() re-resolves.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    from nutrition_app.persistence import database as db_mod
    from nutrition_app.persistence import init_db

    db_mod.reset_engine_for_tests()
    engine = db_mod.get_engine()
    init_db(engine)
    yield engine
    db_mod.reset_engine_for_tests()


@pytest.fixture
def db_session(sqlite_engine):
    """ORM session bound to the in-memory engine."""
    from nutrition_app.persistence import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
