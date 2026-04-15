"""Tests for pipewatch.drift and pipewatch.drift_reporter."""
from __future__ import annotations

import pytest

from pipewatch.drift import DriftConfig, DriftDetector, DriftResult
from pipewatch.drift_reporter import DriftReporter
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metric(value: float, key: str = "test.metric") -> PipelineMetric:
    return PipelineMetric(
        name=key,
        metric_key=key,
        value=value,
        threshold=ThresholdConfig(warning=80.0, critical=95.0),
    )


def _populated_history(values: list[float], key: str = "test.metric") -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(v, key))
    return h


# ---------------------------------------------------------------------------
# DriftConfig
# ---------------------------------------------------------------------------

class TestDriftConfig:
    def test_defaults(self):
        cfg = DriftConfig()
        assert cfg.min_samples == 10
        assert cfg.warn_threshold == pytest.approx(0.10)
        assert cfg.critical_threshold == pytest.approx(0.25)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            DriftConfig(min_samples=1)

    def test_raises_if_warn_not_positive(self):
        with pytest.raises(ValueError, match="warn_threshold"):
            DriftConfig(warn_threshold=0.0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError, match="critical_threshold"):
            DriftConfig(warn_threshold=0.20, critical_threshold=0.15)

    def test_from_dict_custom(self):
        cfg = DriftConfig.from_dict(
            {"min_samples": 6, "warn_threshold": 0.05, "critical_threshold": 0.15}
        )
        assert cfg.min_samples == 6
        assert cfg.warn_threshold == pytest.approx(0.05)

    def test_to_dict_round_trip(self):
        cfg = DriftConfig(min_samples=8, warn_threshold=0.12, critical_threshold=0.30)
        assert DriftConfig.from_dict(cfg.to_dict()).min_samples == 8


# ---------------------------------------------------------------------------
# DriftDetector
# ---------------------------------------------------------------------------

class TestDriftDetectorAnalyse:
    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history([1.0, 2.0, 3.0])
        detector = DriftDetector(DriftConfig(min_samples=10))
        assert detector.analyse("test.metric", h) is None

    def test_ok_when_no_drift(self):
        # baseline ~10, current ~10 — no shift
        h = _populated_history([10.0] * 20)
        detector = DriftDetector(DriftConfig(min_samples=10))
        result = detector.analyse("test.metric", h)
        assert result is not None
        assert result.status == MetricStatus.OK
        assert result.relative_shift == pytest.approx(0.0)

    def test_warning_on_moderate_shift(self):
        # baseline mean 100, current mean 115 → 15 % shift
        baseline = [100.0] * 10
        current = [115.0] * 10
        h = _populated_history(baseline + current)
        detector = DriftDetector(DriftConfig(min_samples=10))
        result = detector.analyse("test.metric", h)
        assert result is not None
        assert result.status == MetricStatus.WARNING
        assert result.relative_shift == pytest.approx(0.15)

    def test_critical_on_large_shift(self):
        # baseline mean 100, current mean 140 → 40 % shift
        baseline = [100.0] * 10
        current = [140.0] * 10
        h = _populated_history(baseline + current)
        detector = DriftDetector(DriftConfig(min_samples=10))
        result = detector.analyse("test.metric", h)
        assert result is not None
        assert result.status == MetricStatus.CRITICAL

    def test_negative_shift_detected(self):
        baseline = [100.0] * 10
        current = [70.0] * 10
        h = _populated_history(baseline + current)
        detector = DriftDetector(DriftConfig(min_samples=10))
        result = detector.analyse("test.metric", h)
        assert result is not None
        assert result.relative_shift == pytest.approx(-0.30)
        assert result.status == MetricStatus.CRITICAL

    def test_analyse_all_returns_only_sufficient_keys(self):
        h = MetricHistory()
        for v in [100.0] * 20:
            h.record(_make_metric(v, "key.a"))
        # key.b has too few samples
        for v in [50.0] * 3:
            h.record(_make_metric(v, "key.b"))
        detector = DriftDetector(DriftConfig(min_samples=10))
        results = detector.analyse_all(h, ["key.a", "key.b"])
        assert "key.a" in results
        assert "key.b" not in results


# ---------------------------------------------------------------------------
# DriftReporter
# ---------------------------------------------------------------------------

class TestDriftReporter:
    def _make_result(self, key: str, shift: float, status: MetricStatus) -> DriftResult:
        return DriftResult(
            metric_key=key,
            baseline_mean=100.0,
            current_mean=100.0 * (1 + shift),
            relative_shift=shift,
            status=status,
        )

    def test_empty_results_message(self):
        reporter = DriftReporter({})
        assert "no results" in DriftReporter({}).format_text().lower()

    def test_has_results_false_when_empty(self):
        assert not DriftReporter({}).has_results

    def test_has_results_true_when_populated(self):
        r = self._make_result("m", 0.0, MetricStatus.OK)
        assert DriftReporter({"m": r}).has_results

    def test_has_drift_false_when_all_ok(self):
        r = self._make_result("m", 0.0, MetricStatus.OK)
        assert not DriftReporter({"m": r}).has_drift()

    def test_has_drift_true_when_warning(self):
        r = self._make_result("m", 0.15, MetricStatus.WARNING)
        assert DriftReporter({"m": r}).has_drift()

    def test_has_critical_true_when_critical(self):
        r = self._make_result("m", 0.40, MetricStatus.CRITICAL)
        assert DriftReporter({"m": r}).has_critical()

    def test_format_text_contains_key(self):
        r = self._make_result("pipeline.lag", 0.12, MetricStatus.WARNING)
        text = DriftReporter({"pipeline.lag": r}).format_text()
        assert "pipeline.lag" in text

    def test_format_text_contains_status_label(self):
        r = self._make_result("m", 0.30, MetricStatus.CRITICAL)
        text = DriftReporter({"m": r}).format_text()
        assert "CRIT" in text

    def test_format_json_valid(self):
        import json
        r = self._make_result("m", 0.05, MetricStatus.OK)
        payload = json.loads(DriftReporter({"m": r}).format_json())
        assert "m" in payload
        assert payload["m"]["status"] == "ok"
