"""Tests for pipewatch.watchdog."""
import math
import time

import pytest

from pipewatch.watchdog import Watchdog, WatchdogConfig, WatchdogResult


# ---------------------------------------------------------------------------
# WatchdogConfig
# ---------------------------------------------------------------------------

class TestWatchdogConfig:
    def test_defaults(self):
        cfg = WatchdogConfig()
        assert cfg.stale_after_seconds == 60.0
        assert cfg.critical_after_seconds == 300.0

    def test_raises_if_stale_not_positive(self):
        with pytest.raises(ValueError, match="stale_after_seconds"):
            WatchdogConfig(stale_after_seconds=0)

    def test_raises_if_critical_not_greater_than_stale(self):
        with pytest.raises(ValueError, match="critical_after_seconds"):
            WatchdogConfig(stale_after_seconds=120.0, critical_after_seconds=60.0)

    def test_from_dict_custom(self):
        cfg = WatchdogConfig.from_dict(
            {"stale_after_seconds": 30.0, "critical_after_seconds": 120.0}
        )
        assert cfg.stale_after_seconds == 30.0
        assert cfg.critical_after_seconds == 120.0

    def test_from_dict_defaults_when_missing(self):
        cfg = WatchdogConfig.from_dict({})
        assert cfg.stale_after_seconds == 60.0

    def test_to_dict_round_trip(self):
        cfg = WatchdogConfig(stale_after_seconds=45.0, critical_after_seconds=180.0)
        assert WatchdogConfig.from_dict(cfg.to_dict()).stale_after_seconds == 45.0


# ---------------------------------------------------------------------------
# Watchdog.check
# ---------------------------------------------------------------------------

class TestWatchdogCheck:
    def _wd(self, stale=30.0, critical=90.0):
        return Watchdog(WatchdogConfig(stale_after_seconds=stale, critical_after_seconds=critical))

    def test_fresh_metric_not_stale(self):
        wd = self._wd()
        now = time.time()
        wd.touch("cpu", ts=now - 5)
        result = wd.check("cpu", now=now)
        assert not result.is_stale
        assert not result.is_critical

    def test_stale_but_not_critical(self):
        wd = self._wd(stale=30.0, critical=90.0)
        now = time.time()
        wd.touch("cpu", ts=now - 60)
        result = wd.check("cpu", now=now)
        assert result.is_stale
        assert not result.is_critical

    def test_critical_metric(self):
        wd = self._wd(stale=30.0, critical=90.0)
        now = time.time()
        wd.touch("cpu", ts=now - 120)
        result = wd.check("cpu", now=now)
        assert result.is_stale
        assert result.is_critical

    def test_never_seen_is_critical(self):
        wd = self._wd()
        wd.touch("other", ts=time.time())
        result = wd.check("unknown_key", now=time.time())
        assert result.last_seen is None
        assert math.isinf(result.age_seconds)
        assert result.is_critical

    def test_to_dict_contains_expected_keys(self):
        wd = self._wd()
        now = time.time()
        wd.touch("cpu", ts=now - 10)
        result = wd.check("cpu", now=now)
        d = result.to_dict()
        assert "is_stale" in d
        assert "is_critical" in d
        assert "age_seconds" in d
        assert "last_seen" in d
