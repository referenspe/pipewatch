"""Tests for pipewatch.skew."""
from __future__ import annotations

import pytest

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.skew import SkewConfig, SkewDetector, _skewness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str, value: float) -> PipelineMetric:
    threshold = ThresholdConfig(warning=80.0, critical=90.0)
    return PipelineMetric(
        key=key,
        value=value,
        status=MetricStatus.OK,
        threshold=threshold,
    )


def _populated_history(key: str, values: list) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(key, v))
    return h


# ---------------------------------------------------------------------------
# SkewConfig
# ---------------------------------------------------------------------------

class TestSkewConfig:
    def test_defaults(self):
        cfg = SkewConfig()
        assert cfg.min_samples == 10
        assert cfg.mild_threshold == 1.0
        assert cfg.severe_threshold == 2.0

    def test_raises_if_min_samples_less_than_three(self):
        with pytest.raises(ValueError, match="min_samples"):
            SkewConfig(min_samples=2)

    def test_raises_if_mild_threshold_zero(self):
        with pytest.raises(ValueError, match="mild_threshold"):
            SkewConfig(mild_threshold=0.0)

    def test_raises_if_severe_not_greater_than_mild(self):
        with pytest.raises(ValueError, match="severe_threshold"):
            SkewConfig(mild_threshold=2.0, severe_threshold=1.5)

    def test_from_dict_custom(self):
        cfg = SkewConfig.from_dict({"min_samples": 5, "mild_threshold": 0.5, "severe_threshold": 1.5})
        assert cfg.min_samples == 5
        assert cfg.mild_threshold == 0.5
        assert cfg.severe_threshold == 1.5

    def test_from_dict_defaults_when_missing(self):
        cfg = SkewConfig.from_dict({})
        assert cfg.min_samples == 10

    def test_to_dict_round_trip(self):
        cfg = SkewConfig(min_samples=6, mild_threshold=0.8, severe_threshold=1.8)
        assert SkewConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()


# ---------------------------------------------------------------------------
# _skewness helper
# ---------------------------------------------------------------------------

def test_skewness_symmetric_returns_near_zero():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert abs(_skewness(values)) < 0.01


def test_skewness_constant_returns_zero():
    assert _skewness([3.0] * 10) == 0.0


def test_skewness_right_skewed_positive():
    values = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 5.0, 20.0]
    assert _skewness(values) > 0


# ---------------------------------------------------------------------------
# SkewDetector
# ---------------------------------------------------------------------------

class TestSkewDetectorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history("cpu", [1.0, 2.0])
        detector = SkewDetector(SkewConfig(min_samples=5))
        assert detector.analyse("cpu", h) is None

    def test_returns_none_for_unknown_key(self):
        h = MetricHistory()
        detector = SkewDetector()
        assert detector.analyse("missing", h) is None

    def test_result_has_correct_sample_count(self):
        values = [float(i) for i in range(15)]
        h = _populated_history("lag", values)
        result = SkewDetector(SkewConfig(min_samples=10)).analyse("lag", h)
        assert result is not None
        assert result.sample_count == 15

    def test_symmetric_data_not_mild_or_severe(self):
        values = [float(i) for i in range(1, 21)]
        h = _populated_history("q", values)
        result = SkewDetector(SkewConfig(min_samples=10)).analyse("q", h)
        assert result is not None
        assert not result.is_mild
        assert not result.is_severe

    def test_severe_skew_detected(self):
        base = [1.0] * 18
        outliers = [100.0, 200.0]
        h = _populated_history("err", base + outliers)
        result = SkewDetector(SkewConfig(min_samples=10, mild_threshold=0.5, severe_threshold=1.0)).analyse("err", h)
        assert result is not None
        assert result.is_severe
        assert not result.is_mild

    def test_to_dict_contains_expected_keys(self):
        values = [float(i) for i in range(15)]
        h = _populated_history("x", values)
        result = SkewDetector(SkewConfig(min_samples=10)).analyse("x", h)
        d = result.to_dict()
        assert "metric_key" in d
        assert "skewness" in d
        assert "sample_count" in d
        assert "is_severe" in d
        assert "is_mild" in d

    def test_analyse_all_skips_insufficient(self):
        h = MetricHistory()
        for v in [1.0, 2.0, 3.0]:
            h.record(_make_metric("short", v))
        for v in range(15):
            h.record(_make_metric("long", float(v)))
        detector = SkewDetector(SkewConfig(min_samples=10))
        results = detector.analyse_all(h, ["short", "long"])
        assert "short" not in results
        assert "long" in results
