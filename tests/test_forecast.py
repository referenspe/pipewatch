"""Tests for pipewatch.forecast and pipewatch.forecast_reporter."""
import pytest

from pipewatch.forecast import Forecaster, ForecastConfidence, _linear_forecast
from pipewatch.forecast_reporter import ForecastReporter
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


def _make_metric(key: str, value: float) -> PipelineMetric:
    cfg = ThresholdConfig(warning=50.0, critical=90.0)
    return PipelineMetric(key=key, value=value, thresholds=cfg, status=MetricStatus.OK)


def _populated_history(key: str, values) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(key, v))
    return h


# ---------------------------------------------------------------------------
# _linear_forecast
# ---------------------------------------------------------------------------

class TestLinearForecast:
    def test_constant_series(self):
        result = _linear_forecast([5.0, 5.0, 5.0, 5.0], steps_ahead=1)
        assert abs(result - 5.0) < 1e-9

    def test_increasing_series(self):
        result = _linear_forecast([1.0, 2.0, 3.0, 4.0], steps_ahead=1)
        assert abs(result - 5.0) < 1e-9

    def test_steps_ahead_two(self):
        result = _linear_forecast([0.0, 1.0, 2.0], steps_ahead=2)
        assert abs(result - 4.0) < 1e-9


# ---------------------------------------------------------------------------
# Forecaster
# ---------------------------------------------------------------------------

class TestForecasterInit:
    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            Forecaster(min_samples=1)

    def test_raises_if_steps_ahead_less_than_one(self):
        with pytest.raises(ValueError, match="steps_ahead"):
            Forecaster(steps_ahead=0)

    def test_defaults(self):
        f = Forecaster()
        assert f.min_samples == 3
        assert f.steps_ahead == 1


class TestForecasterForecast:
    def test_returns_none_when_insufficient_data(self):
        h = _populated_history("cpu", [10.0, 20.0])
        f = Forecaster(min_samples=5)
        assert f.forecast("cpu", h) is None

    def test_returns_result_with_correct_key(self):
        h = _populated_history("cpu", [10.0, 20.0, 30.0])
        result = Forecaster().forecast("cpu", h)
        assert result is not None
        assert result.metric_key == "cpu"

    def test_predicted_value_type(self):
        h = _populated_history("mem", [1.0, 2.0, 3.0])
        result = Forecaster().forecast("mem", h)
        assert isinstance(result.predicted_value, float)

    def test_confidence_low_for_small_sample(self):
        h = _populated_history("x", [1.0, 2.0, 3.0])
        result = Forecaster().forecast("x", h)
        assert result.confidence == ForecastConfidence.LOW

    def test_confidence_high_for_large_sample(self):
        h = _populated_history("x", list(range(25)))
        result = Forecaster().forecast("x", h)
        assert result.confidence == ForecastConfidence.HIGH

    def test_forecast_all_returns_list(self):
        h = _populated_history("a", [1.0, 2.0, 3.0])
        h.record(_make_metric("b", 5.0))
        results = Forecaster().forecast_all(h)
        keys = [r.metric_key for r in results]
        assert "a" in keys


# ---------------------------------------------------------------------------
# ForecastReporter
# ---------------------------------------------------------------------------

class TestForecastReporter:
    def _sample_results(self):
        h = _populated_history("latency", [10.0, 12.0, 14.0])
        return Forecaster().forecast_all(h)

    def test_empty_results_message(self):
        reporter = ForecastReporter([])
        assert "No forecast" in reporter.format_text()

    def test_has_results_false_when_empty(self):
        assert not ForecastReporter([]).has_results()

    def test_has_results_true_when_populated(self):
        results = self._sample_results()
        assert ForecastReporter(results).has_results()

    def test_text_contains_metric_key(self):
        results = self._sample_results()
        text = ForecastReporter(results).format_text()
        assert "latency" in text

    def test_json_is_valid(self):
        import json
        results = self._sample_results()
        data = json.loads(ForecastReporter(results).format_json())
        assert "forecasts" in data

    def test_low_confidence_keys_identified(self):
        results = self._sample_results()
        reporter = ForecastReporter(results)
        assert "latency" in reporter.low_confidence_keys()
