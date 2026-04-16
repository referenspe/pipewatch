"""Tests for pipewatch.watermark and pipewatch.watermark_reporter."""
import pytest

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.watermark import WatermarkConfig, WatermarkTracker
from pipewatch.watermark_reporter import WatermarkReporter


def _make_metric(key: str, value: float, status: MetricStatus = MetricStatus.OK) -> PipelineMetric:
    return PipelineMetric(
        key=key,
        value=value,
        status=status,
        threshold=ThresholdConfig(warning=80.0, critical=95.0),
    )


def _populated_history(key: str, values: list) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(key, v))
    return h


class TestWatermarkConfig:
    def test_defaults(self):
        cfg = WatermarkConfig()
        assert cfg.reset_on_critical is False
        assert cfg.track_low is True

    def test_from_dict_custom(self):
        cfg = WatermarkConfig.from_dict({"reset_on_critical": True, "track_low": False})
        assert cfg.reset_on_critical is True
        assert cfg.track_low is False

    def test_from_dict_defaults_when_missing(self):
        cfg = WatermarkConfig.from_dict({})
        assert cfg.reset_on_critical is False
        assert cfg.track_low is True

    def test_to_dict_round_trip(self):
        cfg = WatermarkConfig(reset_on_critical=True, track_low=False)
        assert WatermarkConfig.from_dict(cfg.to_dict()).reset_on_critical is True


class TestWatermarkTracker:
    def test_returns_none_for_unknown_key(self):
        tracker = WatermarkTracker()
        h = MetricHistory()
        assert tracker.evaluate(h, "missing") is None

    def test_high_tracks_maximum(self):
        tracker = WatermarkTracker()
        h = _populated_history("cpu", [10.0, 50.0, 30.0])
        result = tracker.evaluate(h, "cpu")
        assert result.high == 50.0

    def test_low_tracks_minimum(self):
        tracker = WatermarkTracker()
        h = _populated_history("cpu", [10.0, 50.0, 3.0])
        result = tracker.evaluate(h, "cpu")
        assert result.low == 3.0

    def test_low_none_when_disabled(self):
        tracker = WatermarkTracker(config=WatermarkConfig(track_low=False))
        h = _populated_history("cpu", [10.0, 50.0])
        result = tracker.evaluate(h, "cpu")
        assert result.low is None

    def test_reset_on_critical_clears_watermarks(self):
        tracker = WatermarkTracker(config=WatermarkConfig(reset_on_critical=True))
        h = MetricHistory()
        h.record(_make_metric("cpu", 90.0, MetricStatus.CRITICAL))
        result = tracker.evaluate(h, "cpu")
        assert result.reset is True
        assert result.high == 90.0

    def test_evaluate_all_returns_all_keys(self):
        tracker = WatermarkTracker()
        h = MetricHistory()
        h.record(_make_metric("cpu", 10.0))
        h.record(_make_metric("mem", 20.0))
        results = tracker.evaluate_all(h)
        assert set(results.keys()) == {"cpu", "mem"}


class TestWatermarkReporter:
    def test_empty_results_message(self):
        r = WatermarkReporter({})
        assert "No watermark" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert WatermarkReporter({}).has_results() is False

    def test_has_results_true_when_populated(self):
        tracker = WatermarkTracker()
        h = _populated_history("cpu", [10.0])
        results = tracker.evaluate_all(h)
        assert WatermarkReporter(results).has_results() is True

    def test_format_text_contains_key(self):
        tracker = WatermarkTracker()
        h = _populated_history("latency", [5.0, 8.0])
        r = WatermarkReporter(tracker.evaluate_all(h))
        assert "latency" in r.format_text()

    def test_format_json_valid(self):
        import json
        tracker = WatermarkTracker()
        h = _populated_history("cpu", [1.0, 2.0])
        r = WatermarkReporter(tracker.evaluate_all(h))
        data = json.loads(r.format_json())
        assert "cpu" in data
        assert data["cpu"]["high"] == 2.0
