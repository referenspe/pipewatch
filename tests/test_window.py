"""Tests for pipewatch.window."""
import pytest
from unittest.mock import MagicMock

from pipewatch.window import WindowConfig, WindowAggregator, WindowResult


class TestWindowConfig:
    def test_defaults(self):
        c = WindowConfig()
        assert c.size == 10
        assert c.min_samples == 2

    def test_from_dict_custom(self):
        c = WindowConfig.from_dict({"size": 5, "min_samples": 3})
        assert c.size == 5
        assert c.min_samples == 3

    def test_from_dict_defaults_when_missing(self):
        c = WindowConfig.from_dict({})
        assert c.size == 10

    def test_to_dict_round_trip(self):
        c = WindowConfig(size=7, min_samples=3)
        assert WindowConfig.from_dict(c.to_dict()).size == 7

    def test_raises_if_size_zero(self):
        with pytest.raises(ValueError, match="size"):
            WindowConfig(size=0)

    def test_raises_if_min_samples_exceeds_size(self):
        with pytest.raises(ValueError, match="min_samples cannot exceed size"):
            WindowConfig(size=3, min_samples=5)


def _make_history(values):
    from pipewatch.history import MetricSnapshot
    history = MagicMock()
    snapshots = [MagicMock(spec=MetricSnapshot, value=v) for v in values]
    history.recent = MagicMock(return_value=snapshots)
    return history


class TestWindowAggregator:
    def test_returns_none_mean_when_insufficient(self):
        agg = WindowAggregator(WindowConfig(size=5, min_samples=3))
        history = _make_history([1.0])
        result = agg.compute("latency", history)
        assert result.mean is None
        assert not result.sufficient

    def test_computes_mean(self):
        agg = WindowAggregator(WindowConfig(size=5, min_samples=2))
        history = _make_history([2.0, 4.0, 6.0])
        result = agg.compute("latency", history)
        assert result.mean == pytest.approx(4.0)
        assert result.sufficient

    def test_computes_min_max(self):
        agg = WindowAggregator(WindowConfig(size=5, min_samples=2))
        history = _make_history([1.0, 5.0, 3.0])
        result = agg.compute("x", history)
        assert result.minimum == pytest.approx(1.0)
        assert result.maximum == pytest.approx(5.0)

    def test_key_propagated(self):
        agg = WindowAggregator()
        history = _make_history([1.0, 2.0])
        result = agg.compute("my_metric", history)
        assert result.key == "my_metric"

    def test_to_dict_contains_expected_keys(self):
        agg = WindowAggregator(WindowConfig(size=5, min_samples=2))
        history = _make_history([3.0, 6.0])
        d = agg.compute("k", history).to_dict()
        assert "mean" in d
        assert "min" in d
        assert "max" in d
        assert "sample_count" in d
        assert d["sample_count"] == 2
