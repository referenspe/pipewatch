"""Tests for pipewatch.cooldown."""

from datetime import datetime, timedelta

import pytest

from pipewatch.cooldown import CooldownConfig, CooldownTracker


# ---------------------------------------------------------------------------
# CooldownConfig
# ---------------------------------------------------------------------------

class TestCooldownConfig:
    def test_defaults(self):
        cfg = CooldownConfig()
        assert cfg.default_seconds == 300
        assert cfg.per_key == {}

    def test_from_dict_custom(self):
        cfg = CooldownConfig.from_dict({"default_seconds": 60, "per_key": {"cpu": 120}})
        assert cfg.default_seconds == 60
        assert cfg.seconds_for("cpu") == 120

    def test_from_dict_defaults_when_missing(self):
        cfg = CooldownConfig.from_dict({})
        assert cfg.default_seconds == 300

    def test_to_dict_round_trip(self):
        cfg = CooldownConfig(default_seconds=90, per_key={"mem": 45})
        assert CooldownConfig.from_dict(cfg.to_dict()).default_seconds == 90

    def test_seconds_for_falls_back_to_default(self):
        cfg = CooldownConfig(default_seconds=200)
        assert cfg.seconds_for("unknown_key") == 200

    def test_seconds_for_uses_per_key(self):
        cfg = CooldownConfig(default_seconds=200, per_key={"disk": 30})
        assert cfg.seconds_for("disk") == 30


# ---------------------------------------------------------------------------
# CooldownTracker
# ---------------------------------------------------------------------------

def _tracker(default: int = 60, per_key: dict | None = None) -> CooldownTracker:
    return CooldownTracker(CooldownConfig(default_seconds=default, per_key=per_key or {}))


class TestCooldownTracker:
    def test_not_suppressed_before_first_record(self):
        t = _tracker()
        result = t.check("cpu")
        assert result.suppressed is False
        assert result.remaining_seconds == 0.0
        assert result.next_allowed is None

    def test_suppressed_immediately_after_record(self):
        t = _tracker(default=120)
        now = datetime(2024, 1, 1, 12, 0, 0)
        t.record("cpu", now=now)
        result = t.check("cpu", now=now)
        assert result.suppressed is True
        assert result.remaining_seconds == pytest.approx(120.0)

    def test_not_suppressed_after_cooldown_expires(self):
        t = _tracker(default=60)
        start = datetime(2024, 1, 1, 12, 0, 0)
        t.record("cpu", now=start)
        later = start + timedelta(seconds=61)
        result = t.check("cpu", now=later)
        assert result.suppressed is False

    def test_remaining_seconds_decreases_over_time(self):
        t = _tracker(default=100)
        start = datetime(2024, 1, 1, 0, 0, 0)
        t.record("mem", now=start)
        result = t.check("mem", now=start + timedelta(seconds=40))
        assert result.remaining_seconds == pytest.approx(60.0)

    def test_reset_clears_cooldown(self):
        t = _tracker(default=300)
        now = datetime(2024, 6, 1, 9, 0, 0)
        t.record("disk", now=now)
        t.reset("disk")
        result = t.check("disk", now=now)
        assert result.suppressed is False

    def test_active_keys_lists_recorded_keys(self):
        t = _tracker()
        t.record("a")
        t.record("b")
        assert set(t.active_keys()) == {"a", "b"}

    def test_to_dict_contains_expected_fields(self):
        t = _tracker(default=60)
        now = datetime(2024, 1, 1, 0, 0, 0)
        t.record("x", now=now)
        d = t.check("x", now=now).to_dict()
        assert d["key"] == "x"
        assert d["suppressed"] is True
        assert "remaining_seconds" in d
        assert "next_allowed" in d
