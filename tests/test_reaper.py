"""Tests for pipewatch.reaper."""
import pytest
from pipewatch.reaper import Reaper, ReaperConfig, ReapResult


class TestReaperConfig:
    def test_defaults(self):
        cfg = ReaperConfig()
        assert cfg.stale_seconds == 120.0
        assert cfg.critical_seconds == 300.0

    def test_raises_if_stale_not_positive(self):
        with pytest.raises(ValueError):
            ReaperConfig(stale_seconds=0)

    def test_raises_if_critical_not_greater_than_stale(self):
        with pytest.raises(ValueError):
            ReaperConfig(stale_seconds=100, critical_seconds=100)

    def test_from_dict_custom(self):
        cfg = ReaperConfig.from_dict({"stale_seconds": 60, "critical_seconds": 180})
        assert cfg.stale_seconds == 60
        assert cfg.critical_seconds == 180

    def test_from_dict_defaults_when_missing(self):
        cfg = ReaperConfig.from_dict({})
        assert cfg.stale_seconds == 120.0

    def test_to_dict_round_trip(self):
        cfg = ReaperConfig(stale_seconds=45, critical_seconds=200)
        assert ReaperConfig.from_dict(cfg.to_dict()).stale_seconds == 45


class TestReaper:
    def _reaper(self, stale=60, critical=120):
        return Reaper(ReaperConfig(stale_seconds=stale, critical_seconds=critical))

    def test_no_results_when_fresh(self):
        r = self._reaper()
        r.heartbeat("pipe_a", now=1000.0)
        assert r.reap(now=1050.0) == []

    def test_stale_result_returned(self):
        r = self._reaper(stale=60, critical=120)
        r.heartbeat("pipe_a", now=1000.0)
        results = r.reap(now=1070.0)
        assert len(results) == 1
        assert results[0].key == "pipe_a"
        assert not results[0].is_critical

    def test_critical_result_returned(self):
        r = self._reaper(stale=60, critical=120)
        r.heartbeat("pipe_a", now=1000.0)
        results = r.reap(now=1130.0)
        assert results[0].is_critical

    def test_multiple_keys(self):
        r = self._reaper(stale=60, critical=120)
        r.heartbeat("a", now=1000.0)
        r.heartbeat("b", now=1000.0)
        results = r.reap(now=1070.0)
        assert len(results) == 2

    def test_remove_drops_key(self):
        r = self._reaper(stale=60, critical=120)
        r.heartbeat("pipe_a", now=1000.0)
        r.remove("pipe_a")
        assert r.reap(now=1070.0) == []

    def test_keys_returns_registered(self):
        r = self._reaper()
        r.heartbeat("x")
        assert "x" in r.keys()

    def test_to_dict_contains_key(self):
        result = ReapResult(key="k", last_seen=100.0, age_seconds=65.0, is_critical=False)
        d = result.to_dict()
        assert d["key"] == "k"
        assert d["is_critical"] is False
