"""Tests for pipewatch.debounce."""
import pytest

from pipewatch.debounce import Debounce Config, Debouncer, DebounceResult
from pipewatch.metrics import MetricStatus


# ---------------------------------------------------------------------------
# DebounceConfig
# ---------------------------------------------------------------------------

class TestDebounceConfig:
    def test_defaults(self):
        cfg = DebounceConfig()
        assert cfg.min_consecutive == 2
        assert cfg.reset_on_ok is True

    def test_from_dict_custom(self):
        cfg = DebounceConfig.from_dict({"min_consecutive": 3, "reset_on_ok": False})
        assert cfg.min_consecutive == 3
        assert cfg.reset_on_ok is False

    def test_from_dict_defaults_when_missing(self):
        cfg = DebounceConfig.from_dict({})
        assert cfg.min_consecutive == 2
        assert cfg.reset_on_ok is True

    def test_to_dict_round_trip(self):
        cfg = DebounceConfig(min_consecutive=4, reset_on_ok=False)
        assert DebounceConfig.from_dict(cfg.to_dict()).min_consecutive == 4


# ---------------------------------------------------------------------------
# Debouncer
# ---------------------------------------------------------------------------

class TestDebouncer:
    def _debouncer(self, min_consecutive=2, reset_on_ok=True):
        return Debouncer(DebounceConfig(min_consecutive=min_consecutive, reset_on_ok=reset_on_ok))

    def test_ok_never_fires(self):
        d = self._debouncer()
        result = d.evaluate("cpu", MetricStatus.OK)
        assert result.fired is False

    def test_single_warning_does_not_fire_when_min_is_two(self):
        d = self._debouncer(min_consecutive=2)
        result = d.evaluate("cpu", MetricStatus.WARNING)
        assert result.fired is False
        assert result.consecutive == 1

    def test_fires_after_min_consecutive_warnings(self):
        d = self._debouncer(min_consecutive=2)
        d.evaluate("cpu", MetricStatus.WARNING)
        result = d.evaluate("cpu", MetricStatus.WARNING)
        assert result.fired is True
        assert result.consecutive == 2

    def test_fires_on_every_check_beyond_threshold(self):
        d = self._debouncer(min_consecutive=2)
        for _ in range(2):
            d.evaluate("cpu", MetricStatus.WARNING)
        result = d.evaluate("cpu", MetricStatus.WARNING)
        assert result.fired is True
        assert result.consecutive == 3

    def test_ok_resets_counter_when_reset_on_ok_true(self):
        d = self._debouncer(min_consecutive=2, reset_on_ok=True)
        d.evaluate("cpu", MetricStatus.WARNING)
        d.evaluate("cpu", MetricStatus.OK)
        result = d.evaluate("cpu", MetricStatus.WARNING)
        assert result.consecutive == 1
        assert result.fired is False

    def test_ok_does_not_reset_counter_when_reset_on_ok_false(self):
        d = self._debouncer(min_consecutive=3, reset_on_ok=False)
        d.evaluate("cpu", MetricStatus.WARNING)
        d.evaluate("cpu", MetricStatus.OK)   # should NOT reset
        result = d.evaluate("cpu", MetricStatus.WARNING)
        assert result.consecutive == 2

    def test_manual_reset_clears_state(self):
        d = self._debouncer(min_consecutive=2)
        d.evaluate("cpu", MetricStatus.WARNING)
        d.reset("cpu")
        result = d.evaluate("cpu", MetricStatus.WARNING)
        assert result.consecutive == 1
        assert result.fired is False

    def test_independent_keys_tracked_separately(self):
        d = self._debouncer(min_consecutive=2)
        d.evaluate("cpu", MetricStatus.WARNING)
        result = d.evaluate("mem", MetricStatus.WARNING)
        assert result.consecutive == 1
        assert result.fired is False

    def test_result_to_dict_contains_fired(self):
        d = self._debouncer(min_consecutive=1)
        result = d.evaluate("cpu", MetricStatus.CRITICAL)
        data = result.to_dict()
        assert data["fired"] is True
        assert data["metric_key"] == "cpu"
