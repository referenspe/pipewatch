"""Tests for pipewatch.trend."""

from __future__ import annotations

import pytest

from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.metrics import MetricStatus
from pipewatch.trend import TrendAnalyser, TrendDirection, TrendResult


def _make_history(key: str, values: list[float]) -> MetricHistory:
    history = MetricHistory()
    for v in values:
        snap = MetricSnapshot(key=key, value=v, status=MetricStatus.OK, timestamp=0.0)
        history.record(snap)
    return history


class TestTrendAnalyserInit:
    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError):
            TrendAnalyser(min_samples=1)

    def test_default_min_samples(self):
        analyser = TrendAnalyser()
        assert analyser.min_samples == 3


class TestTrendAnalyserAnalyse:
    def test_unknown_when_insufficient_samples(self):
        history = _make_history("cpu", [10.0, 20.0])  # only 2, default needs 3
        analyser = TrendAnalyser()
        result = analyser.analyse("cpu", history)
        assert result.direction == TrendDirection.UNKNOWN
        assert result.slope is None
        assert result.sample_count == 2

    def test_rising_trend(self):
        history = _make_history("cpu", [10.0, 20.0, 30.0, 40.0])
        analyser = TrendAnalyser()
        result = analyser.analyse("cpu", history)
        assert result.direction == TrendDirection.RISING
        assert result.slope == pytest.approx(10.0)

    def test_falling_trend(self):
        history = _make_history("cpu", [40.0, 30.0, 20.0, 10.0])
        analyser = TrendAnalyser()
        result = analyser.analyse("cpu", history)
        assert result.direction == TrendDirection.FALLING
        assert result.slope == pytest.approx(-10.0)

    def test_stable_trend_within_threshold(self):
        history = _make_history("cpu", [10.0, 10.03, 10.01, 10.02])
        analyser = TrendAnalyser(stable_threshold=0.05)
        result = analyser.analyse("cpu", history)
        assert result.direction == TrendDirection.STABLE

    def test_result_key_matches_input(self):
        history = _make_history("latency", [1.0, 2.0, 3.0])
        analyser = TrendAnalyser()
        result = analyser.analyse("latency", history)
        assert result.key == "latency"

    def test_sample_count_in_result(self):
        history = _make_history("cpu", [1.0, 2.0, 3.0, 4.0])
        analyser = TrendAnalyser()
        result = analyser.analyse("cpu", history)
        assert result.sample_count == 4


class TestTrendResult:
    def test_to_dict_keys(self):
        result = TrendResult(
            key="cpu",
            direction=TrendDirection.RISING,
            slope=5.0,
            sample_count=4,
        )
        d = result.to_dict()
        assert set(d.keys()) == {"key", "direction", "slope", "sample_count"}

    def test_to_dict_direction_is_string(self):
        result = TrendResult(
            key="cpu",
            direction=TrendDirection.STABLE,
            slope=0.0,
            sample_count=3,
        )
        assert result.to_dict()["direction"] == "stable"


class TestTrendAnalyserAnalyseAll:
    def test_returns_result_per_key(self):
        history = MetricHistory()
        for v in [1.0, 2.0, 3.0]:
            history.record(MetricSnapshot(key="cpu", value=v, status=MetricStatus.OK, timestamp=0.0))
            history.record(MetricSnapshot(key="mem", value=v * 2, status=MetricStatus.OK, timestamp=0.0))
        analyser = TrendAnalyser()
        results = analyser.analyse_all(history)
        keys = {r.key for r in results}
        assert keys == {"cpu", "mem"}
