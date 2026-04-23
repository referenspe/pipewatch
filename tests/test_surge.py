"""Tests for pipewatch.surge."""
import pytest

from pipewatch.surge import SurgeConfig, SurgeDetector, SurgeResult
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.history import MetricHistory


def _make_metric(key: str, value: float) -> PipelineMetric:
    return PipelineMetric(
        key=key,
        value=value,
        threshold=ThresholdConfig(warning=50.0, critical=90.0),
    )


def _populated_history(key: str, values: list) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(key, v))
    return h


class TestSurgeConfig:
    def test_defaults(self):
        cfg = SurgeConfig()
        assert cfg.min_samples == 3
        assert cfg.warn_multiplier == 2.0
        assert cfg.critical_multiplier == 4.0

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            SurgeConfig(min_samples=1)

    def test_raises_if_warn_multiplier_not_greater_than_one(self):
        with pytest.raises(ValueError, match="warn_multiplier"):
            SurgeConfig(warn_multiplier=1.0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError, match="critical_multiplier"):
            SurgeConfig(warn_multiplier=2.0, critical_multiplier=2.0)

    def test_from_dict_custom(self):
        cfg = SurgeConfig.from_dict({"min_samples": 5, "warn_multiplier": 3.0, "critical_multiplier": 6.0})
        assert cfg.min_samples == 5
        assert cfg.warn_multiplier == 3.0
        assert cfg.critical_multiplier == 6.0

    def test_from_dict_defaults_when_missing(self):
        cfg = SurgeConfig.from_dict({})
        assert cfg.min_samples == 3

    def test_to_dict_round_trip(self):
        cfg = SurgeConfig(min_samples=4, warn_multiplier=2.5, critical_multiplier=5.0)
        assert SurgeConfig.from_dict(cfg.to_dict()).min_samples == 4


class TestSurgeDetectorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history("q", [10.0, 20.0])
        detector = SurgeDetector(SurgeConfig(min_samples=3))
        assert detector.analyse("q", h) is None

    def test_returns_none_for_unknown_key(self):
        h = MetricHistory()
        detector = SurgeDetector()
        assert detector.analyse("missing", h) is None

    def test_ok_when_no_surge(self):
        h = _populated_history("cpu", [10.0, 10.0, 11.0])
        result = SurgeDetector().analyse("cpu", h)
        assert result is not None
        assert result.status == MetricStatus.OK

    def test_warning_when_moderate_surge(self):
        # baseline mean = 10, latest = 25 => multiplier = 2.5
        h = _populated_history("cpu", [10.0, 10.0, 25.0])
        result = SurgeDetector().analyse("cpu", h)
        assert result.status == MetricStatus.WARNING

    def test_critical_when_large_surge(self):
        # baseline mean = 10, latest = 50 => multiplier = 5.0
        h = _populated_history("cpu", [10.0, 10.0, 50.0])
        result = SurgeDetector().analyse("cpu", h)
        assert result.status == MetricStatus.CRITICAL

    def test_returns_none_when_baseline_mean_is_zero(self):
        h = _populated_history("cpu", [0.0, 0.0, 100.0])
        result = SurgeDetector().analyse("cpu", h)
        assert result is None

    def test_result_contains_metric_key(self):
        h = _populated_history("latency", [5.0, 5.0, 30.0])
        result = SurgeDetector().analyse("latency", h)
        assert result.metric_key == "latency"

    def test_to_dict_contains_expected_keys(self):
        h = _populated_history("cpu", [10.0, 10.0, 25.0])
        result = SurgeDetector().analyse("cpu", h)
        d = result.to_dict()
        assert "metric_key" in d
        assert "status" in d
        assert "multiplier" in d
        assert "baseline_mean" in d
