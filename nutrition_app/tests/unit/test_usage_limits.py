"""
Free-tier usage metering + rate limiting (api/usage.py).

Forces the local SQLite backend (production uses the Supabase usage_daily table)
and verifies free caps block past the limit while pro is unlimited.
"""
import uuid
import pytest
from unittest import mock
from contextlib import closing

from api import usage


@pytest.fixture
def uid():
    u = "test_" + uuid.uuid4().hex[:8]
    yield u
    try:
        with closing(usage._conn()) as c:
            c.execute("DELETE FROM usage_daily WHERE user_id=?", (u,))
    except Exception:
        pass


def test_free_camera_cap_blocks_past_limit(uid):
    limit = usage.FREE_LIMITS["camera"]
    with mock.patch("api.usage._use_sb", return_value=False), \
         mock.patch("api.usage.get_tier", return_value="free"):
        for i in range(limit):
            g = usage.check_and_consume(uid, "camera")
            assert g["allowed"], f"scan {i+1} should be allowed"
        blocked = usage.check_and_consume(uid, "camera")
        assert not blocked["allowed"]
        assert blocked["remaining"] == 0


def test_pro_user_is_unlimited(uid):
    with mock.patch("api.usage._use_sb", return_value=False), \
         mock.patch("api.usage.get_tier", return_value="pro"):
        for _ in range(usage.FREE_LIMITS["camera"] + 5):
            g = usage.check_and_consume(uid, "camera")
            assert g["allowed"]
            assert g["limit"] is None


def test_check_does_not_consume(uid):
    with mock.patch("api.usage._use_sb", return_value=False), \
         mock.patch("api.usage.get_tier", return_value="free"):
        before = usage.get_count(uid, "camera")
        usage.check(uid, "camera")
        usage.check(uid, "camera")
        assert usage.get_count(uid, "camera") == before


def test_features_are_independent(uid):
    with mock.patch("api.usage._use_sb", return_value=False), \
         mock.patch("api.usage.get_tier", return_value="free"):
        usage.check_and_consume(uid, "camera")
        # chat count must be unaffected by camera usage
        assert usage.get_count(uid, "chat") == 0
