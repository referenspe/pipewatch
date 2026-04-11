"""Tests for pipewatch.correlation."""
from __future__ import annotations

import pytest

from pipewatch.history import MetricHistory
from pipewatch.correlation import (
    CorrelationAnalyser,
    CorrelationStrength,
    _pearson,
    _classify,
)


def _make_history(key: str, values: list) -> MetricHistory:
    from pipewatch.metrics import PipelineMetric, MetricStatus, ThresholdConfig
    from pipewatch.history import MetricSnapshot
    import datetime

    h = MetricHistory(metric_key=key)
    for i, v in enumerate(values):
        snap = MetricSnapshot(
            metric_key=key,
            value=v,
            status=MetricStatus.OK,
            timestamp=datetime.datetime(2024, 1, 1, 0, i),
        )
        h.snapshots.append(snap)
    return h


class TestPearson:
    def test_perfect_positive(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert abs(_pearson(xs, xs) - 1.0) < 1e-9

    def test_perfect_negative(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert abs(_pearson(xs, ys) + 1.0) < 1e-9

    def test_constant_series_returns_zero(self):
        xs = [3.0, 3.0, 3.0]
        ys = [1.0, 2.0, 3.0]
        assert _pearson(xs, ys) == 0.0

    def test_short_series_returns_zero(self):
        assert _pearson([1.0], [1.0]) == 0.0


class TestClassify:
    def test_strong_positive(self):
        assert _classify(0.85) == CorrelationStrength.STRONG

    def test_strong_negative(self):
        assert _classify(-0.75) == CorrelationStrength.STRONG

    def test_moderate(self):
        assert _classify(0.55) == CorrelationStrength.MODERATE

    def test_weak(self):
        assert _classify(0.2) == CorrelationStrength.WEAK

    def test_none(self):
        assert _classify(0.05) == CorrelationStrength.NONE


class TestCorrelationAnalyser:
    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError):
            CorrelationAnalyser(min_samples=1)

    def test_returns_none_when_insufficient_samples(self):
        ha = _make_history("a", [1.0, 2.0])
        hb = _make_history("b", [2.0, 4.0])
        analyser = CorrelationAnalyser(min_samples=5)
        assert analyser.analyse(ha, hb) is None

    def test_returns_result_for_sufficient_samples(self):
        vals = [float(i) for i in range(10)]
        ha = _make_history("a", vals)
        hb = _make_history("b", vals)
        analyser = CorrelationAnalyser(min_samples=5)
        result = analyser.analyse(ha, hb)
        assert result is not None
        assert result.key_a == "a"
        assert result.key_b == "b"
        assert result.strength == CorrelationStrength.STRONG

    def test_analyse_all_returns_pairs(self):
        vals = [float(i) for i in range(10)]
        histories = {
            "x": _make_history("x", vals),
            "y": _make_history("y", vals),
            "z": _make_history("z", [v * 2 for v in vals]),
        }
        analyser = CorrelationAnalyser(min_samples=5)
        results = analyser.analyse_all(histories)
        assert len(results) == 3
        keys = {(r.key_a, r.key_b) for r in results}
        assert ("x", "y") in keys

    def test_sample_count_uses_shorter_history(self):
        ha = _make_history("a", [float(i) for i in range(10)])
        hb = _make_history("b", [float(i) for i in range(7)])
        analyser = CorrelationAnalyser(min_samples=5)
        result = analyser.analyse(ha, hb)
        assert result is not None
        assert result.sample_count == 7
