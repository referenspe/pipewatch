"""Tests for pipewatch.smoothing and pipewatch.smoothing_reporter."""
import json
import pytest

from pipewatch.smoothing import (
    MetricSmoother,
    SmoothingConfig,
    SmoothingResult,
    SmoothedSeries,
)
from pipewatch.smoothing_reporter import SmoothingReporter


# ---------------------------------------------------------------------------
# SmoothingConfig
# ---------------------------------------------------------------------------

class TestSmoothingConfig:
    def test_defaults(self):
        cfg = SmoothingConfig()
        assert cfg.alpha == 0.3
        assert cfg.min_samples == 2

    def test_from_dict_custom(self):
        cfg = SmoothingConfig.from_dict({"alpha": 0.5, "min_samples": 3})
        assert cfg.alpha == 0.5
        assert cfg.min_samples == 3

    def test_from_dict_defaults_when_missing(self):
        cfg = SmoothingConfig.from_dict({})
        assert cfg.alpha == 0.3

    def test_to_dict_round_trip(self):
        cfg = SmoothingConfig(alpha=0.2, min_samples=4)
        assert SmoothingConfig.from_dict(cfg.to_dict()).alpha == 0.2

    def test_raises_if_alpha_zero(self):
        with pytest.raises(ValueError, match="alpha"):
            SmoothingConfig(alpha=0.0)

    def test_raises_if_alpha_above_one(self):
        with pytest.raises(ValueError, match="alpha"):
            SmoothingConfig(alpha=1.1)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            SmoothingConfig(min_samples=1)


# ---------------------------------------------------------------------------
# MetricSmoother
# ---------------------------------------------------------------------------

class TestMetricSmootherSmooth:
    def test_returns_none_when_too_few_samples(self):
        smoother = MetricSmoother(SmoothingConfig(min_samples=3))
        assert smoother.smooth("cpu", [1.0, 2.0]) is None

    def test_returns_series_with_correct_key(self):
        smoother = MetricSmoother()
        result = smoother.smooth("cpu", [1.0, 2.0, 3.0])
        assert result is not None
        assert result.key == "cpu"

    def test_smoothed_length_matches_values(self):
        smoother = MetricSmoother()
        result = smoother.smooth("cpu", [10.0, 20.0, 30.0])
        assert len(result.smoothed) == 3

    def test_constant_series_ema_equals_constant(self):
        smoother = MetricSmoother(SmoothingConfig(alpha=0.5))
        result = smoother.smooth("x", [5.0, 5.0, 5.0, 5.0])
        assert abs(result.latest_smoothed - 5.0) < 1e-9

    def test_latest_smoothed_state_stored(self):
        smoother = MetricSmoother()
        smoother.smooth("mem", [1.0, 2.0, 3.0])
        assert smoother.latest_smoothed("mem") is not None

    def test_latest_smoothed_none_for_unknown_key(self):
        smoother = MetricSmoother()
        assert smoother.latest_smoothed("unknown") is None

    def test_smooth_all_returns_result(self):
        smoother = MetricSmoother()
        res = smoother.smooth_all({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        assert len(res.series) == 2

    def test_smooth_all_skips_short_series(self):
        smoother = MetricSmoother(SmoothingConfig(min_samples=3))
        res = smoother.smooth_all({"a": [1.0, 2.0], "b": [1.0, 2.0, 3.0]})
        assert len(res.series) == 1
        assert res.series[0].key == "b"


# ---------------------------------------------------------------------------
# SmoothingReporter
# ---------------------------------------------------------------------------

class TestSmoothingReporter:
    def _make_reporter(self, keys=("cpu",)) -> SmoothingReporter:
        smoother = MetricSmoother()
        series_map = {k: [float(i) for i in range(1, 6)] for k in keys}
        result = smoother.smooth_all(series_map)
        return SmoothingReporter(result)

    def test_empty_results_message(self):
        reporter = SmoothingReporter(SmoothingResult())
        assert "no series" in reporter.format_text()

    def test_has_results_false_when_empty(self):
        assert not SmoothingReporter(SmoothingResult()).has_results()

    def test_has_results_true_when_populated(self):
        assert self._make_reporter().has_results()

    def test_format_text_contains_key(self):
        text = self._make_reporter(keys=("latency",)).format_text()
        assert "latency" in text

    def test_format_text_contains_ema_label(self):
        text = self._make_reporter().format_text()
        assert "ema=" in text

    def test_format_json_valid(self):
        reporter = self._make_reporter()
        data = json.loads(reporter.format_json())
        assert "series" in data

    def test_series_count_matches(self):
        reporter = self._make_reporter(keys=("a", "b", "c"))
        assert reporter.series_count == 3
