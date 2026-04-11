"""Tests for pipewatch.anomaly."""

import pytest

from pipewatch.anomaly import AnomalyDetector, AnomalyLevel
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


def _make_metric(key: str, value: float) -> PipelineMetric:
    cfg = ThresholdConfig(warning=50.0, critical=90.0)
    return PipelineMetric(
        key=key,
        value=value,
        status=MetricStatus.OK,
        threshold=cfg,
    )


def _populated_history(values, key="latency") -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(key, v))
    return h


class TestAnomalyDetectorInit:
    def test_raises_if_severe_not_greater_than_mild(self):
        with pytest.raises(ValueError):
            AnomalyDetector(mild_threshold=3.0, severe_threshold=2.0)

    def test_raises_if_mild_threshold_zero(self):
        with pytest.raises(ValueError):
            AnomalyDetector(mild_threshold=0.0)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError):
            AnomalyDetector(min_samples=1)

    def test_defaults_are_valid(self):
        d = AnomalyDetector()
        assert d.mild_threshold == 2.0
        assert d.severe_threshold == 3.5
        assert d.min_samples == 5


class TestAnomalyDetectorDetect:
    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history([1.0, 2.0, 3.0])  # only 3, default min=5
        d = AnomalyDetector()
        assert d.detect(h, "latency") is None

    def test_returns_none_for_unknown_key(self):
        h = MetricHistory()
        d = AnomalyDetector()
        assert d.detect(h, "missing") is None

    def test_level_none_for_normal_value(self):
        h = _populated_history([10.0, 10.1, 9.9, 10.0, 10.05, 10.02])
        d = AnomalyDetector()
        result = d.detect(h, "latency")
        assert result is not None
        assert result.level == AnomalyLevel.NONE

    def test_level_severe_for_spike(self):
        normal = [10.0] * 20
        h = _populated_history(normal + [500.0])
        d = AnomalyDetector()
        result = d.detect(h, "latency")
        assert result is not None
        assert result.level == AnomalyLevel.SEVERE

    def test_z_score_is_positive_for_high_spike(self):
        h = _populated_history([1.0] * 20 + [100.0])
        d = AnomalyDetector()
        result = d.detect(h, "latency")
        assert result.z_score > 0

    def test_to_dict_contains_expected_keys(self):
        h = _populated_history([10.0] * 10)
        d = AnomalyDetector()
        result = d.detect(h, "latency")
        assert result is not None
        keys = result.to_dict().keys()
        assert "metric_key" in keys
        assert "z_score" in keys
        assert "level" in keys


class TestDetectAll:
    def test_returns_results_for_all_keys(self):
        h = MetricHistory()
        for v in [10.0] * 10:
            h.record(_make_metric("latency", v))
            h.record(_make_metric("error_rate", v * 0.1))
        d = AnomalyDetector()
        results = d.detect_all(h)
        keys = {r.metric_key for r in results}
        assert "latency" in keys
        assert "error_rate" in keys
