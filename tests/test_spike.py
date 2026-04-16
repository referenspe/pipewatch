"""Tests for pipewatch.spike and pipewatch.spike_reporter."""
import math
import pytest

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.spike import SpikeConfig, SpikeDetector, SpikeResult
from pipewatch.spike_reporter import SpikeReporter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str, value: float) -> PipelineMetric:
    cfg = ThresholdConfig(warning=80.0, critical=90.0)
    return PipelineMetric(
        key=key, value=value, status=MetricStatus.OK, threshold=cfg
    )


def _populated_history(values: list) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric("cpu", v))
    return h


# ---------------------------------------------------------------------------
# SpikeConfig
# ---------------------------------------------------------------------------

class TestSpikeConfig:
    def test_defaults(self):
        cfg = SpikeConfig()
        assert cfg.min_samples == 5
        assert cfg.multiplier == 2.5
        assert cfg.lookback == 20

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            SpikeConfig(min_samples=1)

    def test_raises_if_multiplier_not_positive(self):
        with pytest.raises(ValueError, match="multiplier"):
            SpikeConfig(multiplier=0.0)

    def test_raises_if_lookback_less_than_min_samples(self):
        with pytest.raises(ValueError, match="lookback"):
            SpikeConfig(min_samples=10, lookback=5)

    def test_from_dict_custom(self):
        cfg = SpikeConfig.from_dict(
            {"min_samples": 3, "multiplier": 3.0, "lookback": 10}
        )
        assert cfg.min_samples == 3
        assert cfg.multiplier == 3.0
        assert cfg.lookback == 10

    def test_to_dict_round_trip(self):
        cfg = SpikeConfig(min_samples=4, multiplier=2.0, lookback=15)
        assert SpikeConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()


# ---------------------------------------------------------------------------
# SpikeDetector
# ---------------------------------------------------------------------------

class TestSpikeDetector:
    def test_returns_none_for_unknown_key(self):
        h = MetricHistory()
        detector = SpikeDetector()
        assert detector.analyse("missing", h) is None

    def test_returns_none_when_insufficient_samples(self):
        h = _populated_history([1.0, 2.0, 3.0])  # < min_samples=5
        detector = SpikeDetector()
        assert detector.analyse("cpu", h) is None

    def test_no_spike_for_stable_series(self):
        h = _populated_history([10.0] * 10)
        result = SpikeDetector().analyse("cpu", h)
        assert result is not None
        assert not result.is_spike

    def test_spike_detected_for_large_jump(self):
        # baseline values near 10, then a huge jump
        values = [10.0, 10.1, 9.9, 10.0, 10.1, 9.8, 10.2, 10.0, 9.9, 200.0]
        h = _populated_history(values)
        result = SpikeDetector().analyse("cpu", h)
        assert result is not None
        assert result.is_spike
        assert result.current_value == 200.0

    def test_result_fields_are_finite(self):
        h = _populated_history([5.0, 6.0, 5.5, 6.0, 5.8, 6.1])
        result = SpikeDetector().analyse("cpu", h)
        assert result is not None
        assert math.isfinite(result.mean)
        assert math.isfinite(result.std_dev)
        assert math.isfinite(result.threshold)

    def test_analyse_all_returns_all_keys(self):
        h = MetricHistory()
        for key in ("cpu", "mem"):
            for v in [1.0, 1.1, 0.9, 1.0, 1.0, 1.0]:
                h.record(_make_metric(key, v))
        # Override key for second metric
        h2 = MetricHistory()
        for v in [1.0, 1.1, 0.9, 1.0, 1.0, 1.0]:
            h2.record(_make_metric("mem", v))
        results = SpikeDetector().analyse_all(h)
        assert "cpu" in results


# ---------------------------------------------------------------------------
# SpikeReporter
# ---------------------------------------------------------------------------

class TestSpikeReporter:
    def _make_result(self, key: str, is_spike: bool) -> SpikeResult:
        return SpikeResult(
            metric_key=key,
            current_value=100.0 if is_spike else 10.0,
            mean=10.0,
            std_dev=0.5,
            threshold=11.25,
            is_spike=is_spike,
        )

    def test_empty_results_message(self):
        reporter = SpikeReporter({})
        assert "no results" in SpikeReporter({}).format_text()

    def test_has_results_false_when_empty(self):
        assert not SpikeReporter({}).has_results()

    def test_has_results_true_when_populated(self):
        r = SpikeReporter({"cpu": self._make_result("cpu", False)})
        assert r.has_results()

    def test_has_spikes_false_when_none(self):
        r = SpikeReporter({"cpu": self._make_result("cpu", False)})
        assert not r.has_spikes()

    def test_has_spikes_true_when_any(self):
        r = SpikeReporter({"cpu": self._make_result("cpu", True)})
        assert r.has_spikes()

    def test_format_text_contains_key(self):
        r = SpikeReporter({"latency": self._make_result("latency", False)})
        assert "latency" in r.format_text()

    def test_format_text_spike_label(self):
        r = SpikeReporter({"cpu": self._make_result("cpu", True)})
        assert "SPIKE" in r.format_text()

    def test_format_json_contains_key(self):
        r = SpikeReporter({"cpu": self._make_result("cpu", False)})
        assert "cpu" in r.format_json()

    def test_format_json_valid(self):
        import json
        r = SpikeReporter({"cpu": self._make_result("cpu", True)})
        data = json.loads(r.format_json())
        assert "spike_detection" in data
        assert data["spike_detection"]["cpu"]["is_spike"] is True
