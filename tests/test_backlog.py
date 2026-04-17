"""Tests for pipewatch.backlog and pipewatch.backlog_reporter."""
import json
import pytest

from pipewatch.backlog import BacklogConfig, BacklogTracker
from pipewatch.backlog_reporter import BacklogReporter


class TestBacklogConfig:
    def test_defaults(self):
        c = BacklogConfig()
        assert c.warn_depth == 100
        assert c.critical_depth == 500
        assert c.window_size == 5

    def test_raises_if_warn_not_positive(self):
        with pytest.raises(ValueError):
            BacklogConfig(warn_depth=0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError):
            BacklogConfig(warn_depth=200, critical_depth=200)

    def test_raises_if_window_size_less_than_one(self):
        with pytest.raises(ValueError):
            BacklogConfig(window_size=0)

    def test_from_dict_custom(self):
        c = BacklogConfig.from_dict({"warn_depth": 50, "critical_depth": 200, "window_size": 3})
        assert c.warn_depth == 50
        assert c.critical_depth == 200
        assert c.window_size == 3

    def test_from_dict_defaults_when_missing(self):
        c = BacklogConfig.from_dict({})
        assert c.warn_depth == 100

    def test_to_dict_round_trip(self):
        c = BacklogConfig(warn_depth=75, critical_depth=300, window_size=4)
        assert BacklogConfig.from_dict(c.to_dict()).warn_depth == 75


class TestBacklogTracker:
    def _tracker(self):
        return BacklogTracker(config=BacklogConfig(warn_depth=10, critical_depth=50, window_size=3))

    def test_evaluate_returns_none_for_unknown_key(self):
        t = self._tracker()
        assert t.evaluate("missing") is None

    def test_level_ok_when_below_warn(self):
        t = self._tracker()
        t.record("q", 5)
        r = t.evaluate("q")
        assert r.level == "ok"

    def test_level_warn_when_at_warn_threshold(self):
        t = self._tracker()
        t.record("q", 10)
        r = t.evaluate("q")
        assert r.level == "warn"

    def test_level_critical_when_at_critical_threshold(self):
        t = self._tracker()
        t.record("q", 50)
        r = t.evaluate("q")
        assert r.level == "critical"

    def test_is_growing_when_depth_increases(self):
        t = self._tracker()
        t.record("q", 5)
        t.record("q", 8)
        r = t.evaluate("q")
        assert r.is_growing is True

    def test_not_growing_when_depth_decreases(self):
        t = self._tracker()
        t.record("q", 8)
        t.record("q", 5)
        r = t.evaluate("q")
        assert r.is_growing is False

    def test_window_limits_history(self):
        t = self._tracker()
        for v in [1, 2, 3, 4, 5]:
            t.record("q", v)
        r = t.evaluate("q")
        assert len(r.depths) == 3

    def test_evaluate_all_returns_all_keys(self):
        t = self._tracker()
        t.record("a", 1)
        t.record("b", 60)
        results = t.evaluate_all()
        keys = {r.key for r in results}
        assert keys == {"a", "b"}


class TestBacklogReporter:
    def _reporter(self, levels):
        from pipewatch.backlog import BacklogResult
        results = [
            BacklogResult(key=f"q{i}", depths=[v], current_depth=v,
                          is_growing=False, level=lvl)
            for i, (v, lvl) in enumerate(levels)
        ]
        return BacklogReporter(results)

    def test_empty_results_message(self):
        r = BacklogReporter([])
        assert "no data" in r.format_text()

    def test_has_warnings(self):
        r = self._reporter([(15, "warn")])
        assert r.has_warnings()

    def test_has_critical(self):
        r = self._reporter([(60, "critical")])
        assert r.has_critical()

    def test_format_text_contains_key(self):
        r = self._reporter([(5, "ok")])
        assert "q0" in r.format_text()

    def test_format_json_valid(self):
        r = self._reporter([(5, "ok")])
        data = json.loads(r.format_json())
        assert isinstance(data, list)
        assert data[0]["key"] == "q0"
