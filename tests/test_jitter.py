"""Tests for pipewatch.jitter."""
from __future__ import annotations

import pytest

from pipewatch.history import MetricHistory
from pipewatch.jitter import JitterConfig, JitterDetector, JitterResult
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str, value: float) -> PipelineMetric:
    threshold = ThresholdConfig(warning=50.0, critical=90.0)
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
# JitterConfig
# ---------------------------------------------------------------------------

class TestJitterConfig:
    def test_defaults(self):
        cfg = JitterConfig()
        assert cfg.min_samples == 5
        assert cfg.warn_cv == 0.25
        assert cfg.critical_cv == 0.50

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            JitterConfig(min_samples=1)

    def test_raises_if_warn_cv_not_positive(self):
        with pytest.raises(ValueError, match="warn_cv"):
            JitterConfig(warn_cv=0.0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError, match="critical_cv"):
            JitterConfig(warn_cv=0.4, critical_cv=0.3)

    def test_from_dict_custom(self):
        cfg = JitterConfig.from_dict({"min_samples": 10, "warn_cv": 0.1, "critical_cv": 0.3})
        assert cfg.min_samples == 10
        assert cfg.warn_cv == 0.1
        assert cfg.critical_cv == 0.3

    def test_from_dict_defaults_when_missing(self):
        cfg = JitterConfig.from_dict({})
        assert cfg.min_samples == 5

    def test_to_dict_round_trip(self):
        cfg = JitterConfig(min_samples=8, warn_cv=0.2, critical_cv=0.6)
        assert JitterConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()


# ---------------------------------------------------------------------------
# JitterDetector
# ---------------------------------------------------------------------------

class TestJitterDetectorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history("cpu", [10.0, 20.0])  # only 2, min is 5
        detector = JitterDetector()
        assert detector.analyse("cpu", h) is None

    def test_ok_level_for_stable_series(self):
        # all values identical => cv == 0
        h = _populated_history("cpu", [50.0] * 6)
        result = JitterDetector().analyse("cpu", h)
        assert result is not None
        assert result.level == "ok"
        assert result.cv == pytest.approx(0.0)

    def test_warn_level_when_cv_between_thresholds(self):
        # mean=100, std~=30 => cv~=0.30 which is between 0.25 and 0.50
        values = [70.0, 100.0, 130.0, 100.0, 70.0, 130.0]
        h = _populated_history("lag", values)
        result = JitterDetector().analyse("lag", h)
        assert result is not None
        assert result.level == "warn"

    def test_critical_level_when_cv_above_critical(self):
        # very high variance relative to mean
        values = [1.0, 100.0, 1.0, 100.0, 1.0, 100.0]
        h = _populated_history("errors", values)
        result = JitterDetector().analyse("errors", h)
        assert result is not None
        assert result.level == "critical"

    def test_result_fields_populated(self):
        h = _populated_history("cpu", [10.0, 20.0, 30.0, 40.0, 50.0])
        result = JitterDetector().analyse("cpu", h)
        assert result.metric_key == "cpu"
        assert result.sample_count == 5
        assert result.mean == pytest.approx(30.0)

    def test_to_dict_contains_expected_keys(self):
        h = _populated_history("cpu", [10.0] * 5)
        d = JitterDetector().analyse("cpu", h).to_dict()
        assert {"metric_key", "sample_count", "mean", "std_dev", "cv", "level"} <= d.keys()

    def test_analyse_all_skips_keys_with_too_few_samples(self):
        h = MetricHistory()
        h.record(_make_metric("sparse", 1.0))  # only 1 snapshot
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            h.record(_make_metric("dense", v))
        results = JitterDetector().analyse_all(h, ["sparse", "dense"])
        assert "sparse" not in results
        assert "dense" in results
