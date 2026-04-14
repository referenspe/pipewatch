"""Tests for pipewatch.latency and pipewatch.latency_reporter."""
import json
import pytest

from pipewatch.latency import LatencyConfig, LatencyTracker
from pipewatch.latency_reporter import LatencyReporter


# ---------------------------------------------------------------------------
# LatencyConfig
# ---------------------------------------------------------------------------

class TestLatencyConfig:
    def test_defaults(self):
        cfg = LatencyConfig()
        assert cfg.warn_ms == 500.0
        assert cfg.critical_ms == 2000.0
        assert cfg.window_size == 20

    def test_raises_if_warn_not_positive(self):
        with pytest.raises(ValueError, match="warn_ms"):
            LatencyConfig(warn_ms=0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError, match="critical_ms"):
            LatencyConfig(warn_ms=1000.0, critical_ms=500.0)

    def test_raises_if_window_size_less_than_one(self):
        with pytest.raises(ValueError, match="window_size"):
            LatencyConfig(window_size=0)

    def test_from_dict_custom(self):
        cfg = LatencyConfig.from_dict({"warn_ms": 300, "critical_ms": 1000, "window_size": 5})
        assert cfg.warn_ms == 300.0
        assert cfg.critical_ms == 1000.0
        assert cfg.window_size == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = LatencyConfig.from_dict({})
        assert cfg.warn_ms == 500.0

    def test_to_dict_round_trip(self):
        cfg = LatencyConfig(warn_ms=200.0, critical_ms=800.0, window_size=10)
        assert LatencyConfig.from_dict(cfg.to_dict()).warn_ms == 200.0


# ---------------------------------------------------------------------------
# LatencyTracker
# ---------------------------------------------------------------------------

class TestLatencyTracker:
    def _tracker(self, **kwargs):
        return LatencyTracker(config=LatencyConfig(**kwargs))

    def test_evaluate_returns_none_for_unknown_stage(self):
        t = self._tracker()
        assert t.evaluate("missing") is None

    def test_record_and_evaluate_ok(self):
        t = self._tracker(warn_ms=500, critical_ms=2000)
        for _ in range(5):
            t.record("etl", 100.0)
        r = t.evaluate("etl")
        assert r is not None
        assert r.stage == "etl"
        assert not r.is_warning
        assert not r.is_critical

    def test_evaluate_warning(self):
        t = self._tracker(warn_ms=500, critical_ms=2000)
        for _ in range(5):
            t.record("etl", 600.0)
        r = t.evaluate("etl")
        assert r.is_warning
        assert not r.is_critical

    def test_evaluate_critical(self):
        t = self._tracker(warn_ms=500, critical_ms=2000)
        for _ in range(5):
            t.record("etl", 3000.0)
        r = t.evaluate("etl")
        assert r.is_critical

    def test_window_caps_samples(self):
        t = self._tracker(window_size=3)
        for v in [10, 20, 30, 40]:
            t.record("s", float(v))
        r = t.evaluate("s")
        assert len(r.samples) == 3

    def test_evaluate_all_returns_all_stages(self):
        t = self._tracker()
        t.record("a", 100.0)
        t.record("b", 200.0)
        results = t.evaluate_all()
        assert {r.stage for r in results} == {"a", "b"}


# ---------------------------------------------------------------------------
# LatencyReporter
# ---------------------------------------------------------------------------

class TestLatencyReporter:
    def _reporter(self, stages_ms=None):
        tracker = LatencyTracker(config=LatencyConfig(warn_ms=500, critical_ms=2000))
        for stage, values in (stages_ms or {}).items():
            for v in values:
                tracker.record(stage, v)
        return LatencyReporter(tracker.evaluate_all())

    def test_empty_message(self):
        r = LatencyReporter([])
        assert "no data" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert not LatencyReporter([]).has_results()

    def test_has_results_true_when_populated(self):
        r = self._reporter({"s": [100.0]})
        assert r.has_results()

    def test_contains_stage_name(self):
        r = self._reporter({"my_stage": [100.0]})
        assert "my_stage" in r.format_text()

    def test_ok_label(self):
        r = self._reporter({"s": [100.0]})
        assert "OK" in r.format_text()

    def test_warning_label(self):
        r = self._reporter({"s": [600.0]})
        assert "WARNING" in r.format_text()
        assert r.has_warnings()

    def test_critical_label(self):
        r = self._reporter({"s": [3000.0]})
        assert "CRITICAL" in r.format_text()
        assert r.has_criticals()

    def test_format_json_valid(self):
        r = self._reporter({"s": [100.0]})
        data = json.loads(r.format_json())
        assert "latency" in data
        assert data["latency"][0]["stage"] == "s"
