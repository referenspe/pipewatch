"""Tests for pipewatch.cadence."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from pipewatch.cadence import CadenceConfig, CadenceAnalyser
from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.metrics import MetricStatus


def _make_history(key: str, intervals_seconds: list[float]) -> MetricHistory:
    """Build a MetricHistory with snapshots spaced by the given intervals."""
    history = MetricHistory()
    base = datetime(2024, 1, 1, 12, 0, 0)
    t = base
    # first snapshot
    history.record(key, MetricSnapshot(metric_key=key, value=1.0, status=MetricStatus.OK, timestamp=t))
    for gap in intervals_seconds:
        t = t + timedelta(seconds=gap)
        history.record(key, MetricSnapshot(metric_key=key, value=1.0, status=MetricStatus.OK, timestamp=t))
    return history


class TestCadenceConfig:
    def test_defaults(self):
        cfg = CadenceConfig()
        assert cfg.expected_interval_seconds == 60.0
        assert cfg.tolerance_pct == 0.25
        assert cfg.critical_pct == 0.75
        assert cfg.min_samples == 3

    def test_raises_if_interval_not_positive(self):
        with pytest.raises(ValueError):
            CadenceConfig(expected_interval_seconds=0)

    def test_raises_if_tolerance_not_less_than_critical(self):
        with pytest.raises(ValueError):
            CadenceConfig(tolerance_pct=0.8, critical_pct=0.5)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError):
            CadenceConfig(min_samples=1)

    def test_from_dict_custom(self):
        cfg = CadenceConfig.from_dict({"expected_interval_seconds": 30.0, "tolerance_pct": 0.1, "critical_pct": 0.5, "min_samples": 5})
        assert cfg.expected_interval_seconds == 30.0
        assert cfg.min_samples == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = CadenceConfig.from_dict({})
        assert cfg.expected_interval_seconds == 60.0

    def test_to_dict_round_trip(self):
        cfg = CadenceConfig(expected_interval_seconds=45.0, tolerance_pct=0.2, critical_pct=0.6, min_samples=4)
        assert CadenceConfig.from_dict(cfg.to_dict()).expected_interval_seconds == 45.0


class TestCadenceAnalyser:
    def test_insufficient_data_when_too_few_samples(self):
        history = _make_history("cpu", [60.0])  # only 2 snapshots
        analyser = CadenceAnalyser(config=CadenceConfig(min_samples=3))
        result = analyser.analyse("cpu", history)
        assert result.level == "insufficient_data"
        assert result.sample_count == 2

    def test_ok_when_on_schedule(self):
        history = _make_history("cpu", [60.0, 60.0, 60.0, 60.0])
        analyser = CadenceAnalyser()
        result = analyser.analyse("cpu", history)
        assert result.level == "ok"
        assert abs(result.mean_interval - 60.0) < 0.01

    def test_warning_when_moderately_irregular(self):
        # ~40% deviation from 60s expected
        history = _make_history("cpu", [84.0, 84.0, 84.0, 84.0])
        analyser = CadenceAnalyser(config=CadenceConfig(expected_interval_seconds=60.0, tolerance_pct=0.25, critical_pct=0.75))
        result = analyser.analyse("cpu", history)
        assert result.level == "warning"

    def test_critical_when_severely_irregular(self):
        # ~133% deviation
        history = _make_history("cpu", [140.0, 140.0, 140.0, 140.0])
        analyser = CadenceAnalyser(config=CadenceConfig(expected_interval_seconds=60.0, tolerance_pct=0.25, critical_pct=0.75))
        result = analyser.analyse("cpu", history)
        assert result.level == "critical"

    def test_to_dict_contains_expected_keys(self):
        history = _make_history("mem", [60.0, 60.0, 60.0])
        analyser = CadenceAnalyser()
        result = analyser.analyse("mem", history)
        d = result.to_dict()
        assert "metric_key" in d
        assert "mean_interval" in d
        assert "deviation_pct" in d
        assert "level" in d
        assert "sample_count" in d
