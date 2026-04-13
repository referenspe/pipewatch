"""Tests for pipewatch.heartbeat."""

from datetime import datetime, timezone, timedelta

import pytest

from pipewatch.heartbeat import HeartbeatConfig, HeartbeatTracker


# ---------------------------------------------------------------------------
# HeartbeatConfig
# ---------------------------------------------------------------------------

class TestHeartbeatConfig:
    def test_defaults(self):
        cfg = HeartbeatConfig()
        assert cfg.timeout_seconds == 60.0
        assert cfg.critical_seconds == 300.0

    def test_raises_if_timeout_not_positive(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            HeartbeatConfig(timeout_seconds=0)

    def test_raises_if_critical_not_greater_than_timeout(self):
        with pytest.raises(ValueError, match="critical_seconds"):
            HeartbeatConfig(timeout_seconds=60.0, critical_seconds=60.0)

    def test_from_dict_custom(self):
        cfg = HeartbeatConfig.from_dict({"timeout_seconds": 30.0, "critical_seconds": 120.0})
        assert cfg.timeout_seconds == 30.0
        assert cfg.critical_seconds == 120.0

    def test_from_dict_defaults_when_missing(self):
        cfg = HeartbeatConfig.from_dict({})
        assert cfg.timeout_seconds == 60.0
        assert cfg.critical_seconds == 300.0

    def test_to_dict_round_trip(self):
        cfg = HeartbeatConfig(timeout_seconds=45.0, critical_seconds=180.0)
        assert HeartbeatConfig.from_dict(cfg.to_dict()).timeout_seconds == 45.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _tracker() -> HeartbeatTracker:
    return HeartbeatTracker(HeartbeatConfig(timeout_seconds=60.0, critical_seconds=300.0))


# ---------------------------------------------------------------------------
# HeartbeatTracker
# ---------------------------------------------------------------------------

class TestHeartbeatTracker:
    def test_unknown_key_is_critical(self):
        t = _tracker()
        result = t.check("pipe.a", now=_now())
        assert result.is_stale
        assert result.is_critical
        assert result.last_seen is None
        assert result.elapsed_seconds is None

    def test_fresh_ping_is_not_stale(self):
        t = _tracker()
        now = _now()
        t.ping("pipe.a", now=now)
        result = t.check("pipe.a", now=now)
        assert not result.is_stale
        assert not result.is_critical

    def test_stale_but_not_critical(self):
        t = _tracker()
        now = _now()
        t.ping("pipe.a", now=now)
        later = now + timedelta(seconds=90)
        result = t.check("pipe.a", now=later)
        assert result.is_stale
        assert not result.is_critical

    def test_critical_after_long_silence(self):
        t = _tracker()
        now = _now()
        t.ping("pipe.a", now=now)
        later = now + timedelta(seconds=400)
        result = t.check("pipe.a", now=later)
        assert result.is_stale
        assert result.is_critical

    def test_elapsed_seconds_is_correct(self):
        t = _tracker()
        now = _now()
        t.ping("pipe.a", now=now)
        later = now + timedelta(seconds=42)
        result = t.check("pipe.a", now=later)
        assert result.elapsed_seconds == pytest.approx(42.0)

    def test_check_all_returns_all_keys(self):
        t = _tracker()
        now = _now()
        t.ping("pipe.a", now=now)
        t.ping("pipe.b", now=now)
        results = t.check_all(now=now)
        keys = {r.key for r in results}
        assert keys == {"pipe.a", "pipe.b"}

    def test_known_keys(self):
        t = _tracker()
        t.ping("x")
        t.ping("y")
        assert set(t.known_keys()) == {"x", "y"}

    def test_to_dict_contains_key(self):
        t = _tracker()
        now = _now()
        t.ping("pipe.z", now=now)
        result = t.check("pipe.z", now=now)
        d = result.to_dict()
        assert d["key"] == "pipe.z"
        assert d["is_stale"] is False
