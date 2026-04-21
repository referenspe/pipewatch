"""Tests for pipewatch.cardinality."""
from __future__ import annotations

import pytest

from pipewatch.cardinality import CardinalityAnalyser, CardinalityConfig
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


def _make_metric(value: float, key: str = "test_metric") -> PipelineMetric:
    return PipelineMetric(
        key=key,
        value=value,
        threshold=ThresholdConfig(warning=80.0, critical=95.0),
        status=MetricStatus.OK,
    )


def _history_with(values) -> MetricHistory:
    h = MetricHistory()
    for v in values:
        h.record(_make_metric(v))
    return h


# ---------------------------------------------------------------------------
# CardinalityConfig
# ---------------------------------------------------------------------------

class TestCardinalityConfig:
    def test_defaults(self):
        cfg = CardinalityConfig()
        assert cfg.warn_above == 100
        assert cfg.critical_above == 500
        assert cfg.window_size == 1000

    def test_from_dict_custom(self):
        cfg = CardinalityConfig.from_dict(
            {"warn_above": 50, "critical_above": 200, "window_size": 500}
        )
        assert cfg.warn_above == 50
        assert cfg.critical_above == 200
        assert cfg.window_size == 500

    def test_from_dict_defaults_when_missing(self):
        cfg = CardinalityConfig.from_dict({})
        assert cfg.warn_above == 100

    def test_to_dict_round_trip(self):
        cfg = CardinalityConfig(warn_above=10, critical_above=20, window_size=50)
        assert CardinalityConfig.from_dict(cfg.to_dict()).warn_above == 10

    def test_raises_if_warn_not_positive(self):
        with pytest.raises(ValueError):
            CardinalityConfig(warn_above=0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError):
            CardinalityConfig(warn_above=100, critical_above=100)

    def test_raises_if_window_size_less_than_one(self):
        with pytest.raises(ValueError):
            CardinalityConfig(window_size=0)


# ---------------------------------------------------------------------------
# CardinalityAnalyser
# ---------------------------------------------------------------------------

class TestCardinalityAnalyser:
    def test_returns_none_for_empty_history(self):
        analyser = CardinalityAnalyser(CardinalityConfig(warn_above=5, critical_above=10))
        result = analyser.analyse("k", MetricHistory())
        assert result is None

    def test_ok_when_below_warn(self):
        analyser = CardinalityAnalyser(CardinalityConfig(warn_above=5, critical_above=10))
        h = _history_with([1.0, 2.0, 3.0])  # 3 distinct
        result = analyser.analyse("k", h)
        assert result is not None
        assert not result.is_warning
        assert not result.is_critical

    def test_warning_when_between_thresholds(self):
        analyser = CardinalityAnalyser(CardinalityConfig(warn_above=2, critical_above=10))
        h = _history_with([1.0, 2.0, 3.0])  # 3 distinct
        result = analyser.analyse("k", h)
        assert result.is_warning
        assert not result.is_critical

    def test_critical_when_above_critical(self):
        analyser = CardinalityAnalyser(CardinalityConfig(warn_above=1, critical_above=2))
        h = _history_with([1.0, 2.0, 3.0])  # 3 distinct
        result = analyser.analyse("k", h)
        assert result.is_critical

    def test_distinct_count_correct(self):
        analyser = CardinalityAnalyser()
        h = _history_with([1.0, 1.0, 2.0, 3.0, 3.0])
        result = analyser.analyse("k", h)
        assert result.distinct_count == 3

    def test_window_size_limits_snapshots(self):
        analyser = CardinalityAnalyser(
            CardinalityConfig(warn_above=1, critical_above=2, window_size=2)
        )
        # 4 distinct values overall but only last 2 snapshots considered
        h = _history_with([10.0, 20.0, 30.0, 30.0])
        result = analyser.analyse("k", h)
        assert result.distinct_count == 1  # last 2 are both 30.0

    def test_analyse_all_returns_list(self):
        analyser = CardinalityAnalyser(CardinalityConfig(warn_above=5, critical_above=10))
        histories = {
            "a": _history_with([1.0, 2.0]),
            "b": _history_with([1.0]),
        }
        results = analyser.analyse_all(histories)
        keys = {r.key for r in results}
        assert keys == {"a", "b"}

    def test_to_dict_contains_fields(self):
        analyser = CardinalityAnalyser(CardinalityConfig(warn_above=1, critical_above=2))
        h = _history_with([1.0, 2.0, 3.0])
        result = analyser.analyse("mykey", h)
        d = result.to_dict()
        assert d["key"] == "mykey"
        assert "distinct_count" in d
        assert "is_critical" in d
