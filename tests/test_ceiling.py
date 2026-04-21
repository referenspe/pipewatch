"""Tests for pipewatch.ceiling."""
from __future__ import annotations

import pytest

from pipewatch.ceiling import CeilingConfig, CeilingDetector, CeilingResult
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str, value: float) -> PipelineMetric:
    thresholds = ThresholdConfig(warning=50.0, critical=90.0)
    return PipelineMetric(key=key, value=value, thresholds=thresholds)


def _populated_history(key: str, values: list) -> MetricHistory:
    history = MetricHistory()
    for v in values:
        history.record(_make_metric(key, v))
    return history


# ---------------------------------------------------------------------------
# CeilingConfig
# ---------------------------------------------------------------------------

class TestCeilingConfig:
    def test_defaults(self):
        cfg = CeilingConfig()
        assert cfg.proximity == 0.95
        assert cfg.min_samples == 3

    def test_from_dict_custom(self):
        cfg = CeilingConfig.from_dict({"proximity": 0.80, "min_samples": 5})
        assert cfg.proximity == 0.80
        assert cfg.min_samples == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = CeilingConfig.from_dict({})
        assert cfg.proximity == 0.95
        assert cfg.min_samples == 3

    def test_to_dict_round_trip(self):
        cfg = CeilingConfig(proximity=0.88, min_samples=4)
        assert CeilingConfig.from_dict(cfg.to_dict()).proximity == 0.88

    def test_raises_if_proximity_zero(self):
        with pytest.raises(ValueError, match="proximity"):
            CeilingConfig(proximity=0.0)

    def test_raises_if_proximity_one(self):
        with pytest.raises(ValueError, match="proximity"):
            CeilingConfig(proximity=1.0)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            CeilingConfig(min_samples=1)


# ---------------------------------------------------------------------------
# CeilingDetector.analyse
# ---------------------------------------------------------------------------

class TestCeilingDetectorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        history = _populated_history("q", [80.0, 85.0])  # 2 samples, min=3
        detector = CeilingDetector(CeilingConfig(min_samples=3))
        assert detector.analyse("q", history, ceiling=100.0) is None

    def test_ok_when_well_below_ceiling(self):
        history = _populated_history("q", [10.0, 20.0, 30.0])
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=100.0)
        assert result is not None
        assert result.status == MetricStatus.OK

    def test_warning_when_near_ceiling(self):
        history = _populated_history("q", [90.0, 91.0, 96.0])  # 96/100 = 0.96 >= 0.95
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=100.0)
        assert result is not None
        assert result.status == MetricStatus.WARNING

    def test_critical_when_at_or_above_ceiling(self):
        history = _populated_history("q", [99.0, 100.0, 100.0])
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=100.0)
        assert result is not None
        assert result.status == MetricStatus.CRITICAL

    def test_ratio_is_computed_correctly(self):
        history = _populated_history("q", [50.0, 50.0, 50.0])
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=200.0)
        assert result is not None
        assert abs(result.ratio - 0.25) < 1e-9

    def test_zero_ceiling_returns_zero_ratio(self):
        history = _populated_history("q", [0.0, 0.0, 0.0])
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=0.0)
        assert result is not None
        assert result.ratio == 0.0

    def test_sample_count_matches(self):
        history = _populated_history("q", [1.0, 2.0, 3.0, 4.0])
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=10.0)
        assert result is not None
        assert result.sample_count == 4

    def test_to_dict_contains_expected_keys(self):
        history = _populated_history("q", [5.0, 6.0, 7.0])
        detector = CeilingDetector()
        result = detector.analyse("q", history, ceiling=100.0)
        assert result is not None
        d = result.to_dict()
        for k in ("key", "ceiling", "latest", "ratio", "status", "sample_count"):
            assert k in d

    def test_analyse_all_skips_keys_without_enough_data(self):
        history = _populated_history("a", [80.0, 90.0, 95.0])
        # key "b" has no data
        detector = CeilingDetector()
        results = detector.analyse_all(history, {"a": 100.0, "b": 50.0})
        keys = [r.key for r in results]
        assert "a" in keys
        assert "b" not in keys
