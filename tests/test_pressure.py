"""Tests for pipewatch.pressure and pipewatch.pressure_reporter."""
from __future__ import annotations

import pytest

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.pressure import PressureConfig, PressureMonitor
from pipewatch.pressure_reporter import PressureReporter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str, value: float) -> PipelineMetric:
    return PipelineMetric(
        key=key,
        value=value,
        threshold=ThresholdConfig(warning=50.0, critical=90.0),
    )


def _populated_history(key: str, values: list[float]) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(key, v))
    return h


# ---------------------------------------------------------------------------
# PressureConfig
# ---------------------------------------------------------------------------

class TestPressureConfig:
    def test_defaults(self):
        cfg = PressureConfig()
        assert cfg.min_samples == 3
        assert cfg.warn_rate == pytest.approx(0.10)
        assert cfg.critical_rate == pytest.approx(0.25)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            PressureConfig(min_samples=1)

    def test_raises_if_warn_rate_not_positive(self):
        with pytest.raises(ValueError, match="warn_rate"):
            PressureConfig(warn_rate=0.0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError, match="critical_rate"):
            PressureConfig(warn_rate=0.20, critical_rate=0.20)

    def test_from_dict_custom(self):
        cfg = PressureConfig.from_dict(
            {"min_samples": 5, "warn_rate": 0.15, "critical_rate": 0.40}
        )
        assert cfg.min_samples == 5
        assert cfg.warn_rate == pytest.approx(0.15)
        assert cfg.critical_rate == pytest.approx(0.40)

    def test_from_dict_defaults_when_missing(self):
        cfg = PressureConfig.from_dict({})
        assert cfg.min_samples == 3

    def test_to_dict_round_trip(self):
        cfg = PressureConfig(min_samples=4, warn_rate=0.12, critical_rate=0.30)
        assert PressureConfig.from_dict(cfg.to_dict()).min_samples == 4


# ---------------------------------------------------------------------------
# PressureMonitor.analyse
# ---------------------------------------------------------------------------

class TestPressureMonitorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history("q", [1.0, 2.0])  # only 2 < min_samples=3
        monitor = PressureMonitor(PressureConfig(min_samples=3))
        assert monitor.analyse("q", h) is None

    def test_ok_for_flat_series(self):
        h = _populated_history("q", [10.0, 10.0, 10.0, 10.0])
        result = PressureMonitor().analyse("q", h)
        assert result is not None
        assert result.status == MetricStatus.OK

    def test_warning_for_moderate_rise(self):
        # ~15% increase each step
        h = _populated_history("q", [100.0, 115.0, 132.25, 152.0])
        monitor = PressureMonitor(PressureConfig(warn_rate=0.10, critical_rate=0.25))
        result = monitor.analyse("q", h)
        assert result is not None
        assert result.status == MetricStatus.WARNING

    def test_critical_for_steep_rise(self):
        # ~30% increase each step
        h = _populated_history("q", [100.0, 130.0, 169.0, 219.7])
        monitor = PressureMonitor(PressureConfig(warn_rate=0.10, critical_rate=0.25))
        result = monitor.analyse("q", h)
        assert result is not None
        assert result.status == MetricStatus.CRITICAL

    def test_result_key_matches(self):
        h = _populated_history("pipe.lag", [1.0, 1.0, 1.0])
        result = PressureMonitor().analyse("pipe.lag", h)
        assert result is not None
        assert result.key == "pipe.lag"

    def test_sample_count_in_result(self):
        h = _populated_history("x", [1.0, 2.0, 3.0, 4.0])
        result = PressureMonitor().analyse("x", h)
        assert result.sample_count == 4

    def test_to_dict_contains_expected_keys(self):
        h = _populated_history("x", [1.0, 1.1, 1.2])
        result = PressureMonitor().analyse("x", h)
        d = result.to_dict()
        assert "key" in d and "status" in d and "avg_rate" in d


# ---------------------------------------------------------------------------
# PressureReporter
# ---------------------------------------------------------------------------

class TestPressureReporter:
    def _make_reporter(self, statuses: list[MetricStatus]) -> PressureReporter:
        from pipewatch.pressure import PressureResult
        results = {}
        for i, s in enumerate(statuses):
            key = f"metric_{i}"
            results[key] = PressureResult(
                key=key, status=s, avg_rate=0.1, sample_count=4, message="test"
            )
        return PressureReporter(results=results)

    def test_empty_results_message(self):
        r = PressureReporter()
        assert "no results" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert not PressureReporter().has_results

    def test_has_results_true_when_populated(self):
        r = self._make_reporter([MetricStatus.OK])
        assert r.has_results

    def test_has_warnings(self):
        r = self._make_reporter([MetricStatus.OK, MetricStatus.WARNING])
        assert r.has_warnings

    def test_has_critical(self):
        r = self._make_reporter([MetricStatus.CRITICAL])
        assert r.has_critical

    def test_format_text_contains_key(self):
        r = self._make_reporter([MetricStatus.OK])
        assert "metric_0" in r.format_text()

    def test_format_json_is_valid(self):
        import json
        r = self._make_reporter([MetricStatus.WARNING])
        data = json.loads(r.format_json())
        assert "metric_0" in data
