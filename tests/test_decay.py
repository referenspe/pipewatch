"""Tests for pipewatch.decay."""
from __future__ import annotations

import time
import pytest

from pipewatch.decay import DecayConfig, DecayAnalyser, DecayResult
from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.metrics import MetricStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_history(entries: list[tuple[str, float, float]]) -> MetricHistory:
    """entries: list of (key, value, recorded_at_offset_seconds_ago)."""
    now = time.time()
    history = MetricHistory()
    for key, value, age in entries:
        snap = MetricSnapshot(metric_key=key, value=value, status=MetricStatus.OK,
                              recorded_at=now - age)
        history._store.setdefault(key, []).append(snap)
    return history


# ---------------------------------------------------------------------------
# DecayConfig
# ---------------------------------------------------------------------------

class TestDecayConfig:
    def test_defaults(self):
        cfg = DecayConfig()
        assert cfg.half_life == 60.0
        assert cfg.min_samples == 2

    def test_from_dict_custom(self):
        cfg = DecayConfig.from_dict({"half_life": 30.0, "min_samples": 5})
        assert cfg.half_life == 30.0
        assert cfg.min_samples == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = DecayConfig.from_dict({})
        assert cfg.half_life == 60.0
        assert cfg.min_samples == 2

    def test_to_dict_round_trip(self):
        cfg = DecayConfig(half_life=45.0, min_samples=3)
        assert DecayConfig.from_dict(cfg.to_dict()).half_life == 45.0

    def test_raises_if_half_life_not_positive(self):
        with pytest.raises(ValueError, match="half_life"):
            DecayConfig(half_life=0)

    def test_raises_if_min_samples_less_than_two(self):
        with pytest.raises(ValueError, match="min_samples"):
            DecayConfig(min_samples=1)


# ---------------------------------------------------------------------------
# DecayAnalyser
# ---------------------------------------------------------------------------

class TestDecayAnalyser:
    def test_returns_none_for_unknown_key(self):
        history = MetricHistory()
        analyser = DecayAnalyser()
        assert analyser.analyse("missing", history) is None

    def test_insufficient_flagged_when_below_min_samples(self):
        history = _make_history([("cpu", 50.0, 0)])
        analyser = DecayAnalyser(DecayConfig(min_samples=2))
        result = analyser.analyse("cpu", history)
        assert result is not None
        assert result.sufficient is False
        assert result.sample_count == 1

    def test_sufficient_when_enough_samples(self):
        history = _make_history([("cpu", 50.0, 10), ("cpu", 60.0, 0)])
        analyser = DecayAnalyser(DecayConfig(min_samples=2))
        result = analyser.analyse("cpu", history)
        assert result is not None
        assert result.sufficient is True

    def test_recent_sample_weighted_higher(self):
        # Two samples: old=100, recent=0; decayed mean should be closer to 0
        history = _make_history([("val", 100.0, 120), ("val", 0.0, 0)])
        analyser = DecayAnalyser(DecayConfig(half_life=30.0))
        result = analyser.analyse("val", history)
        assert result is not None
        assert result.weighted_mean < 50.0  # recent (0) outweighs old (100)

    def test_equal_weights_when_simultaneous(self):
        history = _make_history([("x", 20.0, 0), ("x", 40.0, 0)])
        analyser = DecayAnalyser()
        result = analyser.analyse("x", history)
        assert result is not None
        assert abs(result.weighted_mean - 30.0) < 1e-4

    def test_analyse_all_returns_results_for_each_key(self):
        history = _make_history([("a", 1.0, 0), ("a", 2.0, 5),
                                  ("b", 5.0, 0), ("b", 6.0, 5)])
        analyser = DecayAnalyser()
        results = analyser.analyse_all(history)
        keys = {r.metric_key for r in results}
        assert keys == {"a", "b"}

    def test_to_dict_contains_expected_fields(self):
        history = _make_history([("m", 10.0, 0), ("m", 20.0, 60)])
        analyser = DecayAnalyser()
        result = analyser.analyse("m", history)
        d = result.to_dict()
        assert "metric_key" in d
        assert "weighted_mean" in d
        assert "sample_count" in d
        assert "sufficient" in d
