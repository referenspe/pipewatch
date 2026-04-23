"""Tests for pipewatch.outlier."""
import pytest

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.outlier import OutlierConfig, OutlierDetector


def _make_metric(value: float) -> PipelineMetric:
    return PipelineMetric(
        key="test.metric",
        value=value,
        threshold=ThresholdConfig(warning=80.0, critical=90.0),
    )


def _populated_history(values, key="test.metric") -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(v))
    return h


class TestOutlierConfig:
    def test_defaults(self):
        cfg = OutlierConfig()
        assert cfg.min_samples == 8
        assert cfg.iqr_multiplier == 1.5
        assert cfg.severe_multiplier == 3.0

    def test_raises_if_min_samples_less_than_four(self):
        with pytest.raises(ValueError, match="min_samples"):
            OutlierConfig(min_samples=3)

    def test_raises_if_iqr_multiplier_not_positive(self):
        with pytest.raises(ValueError, match="iqr_multiplier"):
            OutlierConfig(iqr_multiplier=0.0)

    def test_raises_if_severe_not_greater_than_mild(self):
        with pytest.raises(ValueError, match="severe_multiplier"):
            OutlierConfig(iqr_multiplier=2.0, severe_multiplier=1.5)

    def test_from_dict_custom(self):
        cfg = OutlierConfig.from_dict(
            {"min_samples": 10, "iqr_multiplier": 2.0, "severe_multiplier": 4.0}
        )
        assert cfg.min_samples == 10
        assert cfg.iqr_multiplier == 2.0
        assert cfg.severe_multiplier == 4.0

    def test_from_dict_defaults_when_missing(self):
        cfg = OutlierConfig.from_dict({})
        assert cfg.min_samples == 8

    def test_to_dict_round_trip(self):
        cfg = OutlierConfig(min_samples=12, iqr_multiplier=1.5, severe_multiplier=3.0)
        assert OutlierConfig.from_dict(cfg.to_dict()).min_samples == 12


class TestOutlierDetectorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        history = _populated_history([1.0, 2.0, 3.0])
        detector = OutlierDetector(OutlierConfig(min_samples=8))
        assert detector.analyse("test.metric", history) is None

    def test_ok_for_value_within_fences(self):
        values = [10.0] * 10
        history = _populated_history(values)
        detector = OutlierDetector()
        result = detector.analyse("test.metric", history)
        assert result is not None
        assert result.status == MetricStatus.OK

    def test_warning_for_mild_outlier(self):
        base = [10.0] * 9
        history = _populated_history(base + [50.0])
        detector = OutlierDetector(OutlierConfig(min_samples=8))
        result = detector.analyse("test.metric", history)
        assert result is not None
        assert result.status == MetricStatus.WARNING

    def test_critical_for_severe_outlier(self):
        base = [10.0] * 9
        history = _populated_history(base + [500.0])
        detector = OutlierDetector(OutlierConfig(min_samples=8))
        result = detector.analyse("test.metric", history)
        assert result is not None
        assert result.status == MetricStatus.CRITICAL

    def test_result_contains_metric_key(self):
        history = _populated_history([5.0] * 10)
        result = OutlierDetector().analyse("test.metric", history)
        assert result is not None
        assert result.metric_key == "test.metric"

    def test_to_dict_contains_expected_keys(self):
        history = _populated_history([5.0] * 10)
        result = OutlierDetector().analyse("test.metric", history)
        assert result is not None
        d = result.to_dict()
        for key in ("metric_key", "value", "q1", "q3", "iqr", "lower_fence", "upper_fence", "status"):
            assert key in d

    def test_analyse_all_skips_insufficient(self):
        h = MetricHistory()
        for v in [1.0, 2.0]:
            h.record(_make_metric(v))
        detector = OutlierDetector()
        results = detector.analyse_all(["test.metric"], h)
        assert results == []
