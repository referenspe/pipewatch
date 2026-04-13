"""Tests for pipewatch.checkpoint."""
import time
import pytest
from pipewatch.checkpoint import (
    CheckpointConfig,
    CheckpointEntry,
    CheckpointTracker,
)


# ---------------------------------------------------------------------------
# CheckpointConfig
# ---------------------------------------------------------------------------

class TestCheckpointConfig:
    def test_defaults(self):
        cfg = CheckpointConfig()
        assert cfg.stall_after == 300.0
        assert cfg.max_history == 50

    def test_from_dict_custom(self):
        cfg = CheckpointConfig.from_dict({"stall_after": 60, "max_history": 10})
        assert cfg.stall_after == 60.0
        assert cfg.max_history == 10

    def test_from_dict_defaults_when_missing(self):
        cfg = CheckpointConfig.from_dict({})
        assert cfg.stall_after == 300.0

    def test_to_dict_round_trip(self):
        cfg = CheckpointConfig(stall_after=120.0, max_history=20)
        assert CheckpointConfig.from_dict(cfg.to_dict()).stall_after == 120.0


# ---------------------------------------------------------------------------
# CheckpointTracker — record / evaluate
# ---------------------------------------------------------------------------

class TestCheckpointTracker:
    def _tracker(self, stall_after: float = 300.0) -> CheckpointTracker:
        return CheckpointTracker(CheckpointConfig(stall_after=stall_after))

    def test_evaluate_returns_none_for_unknown_stage(self):
        t = self._tracker()
        assert t.evaluate("missing") is None

    def test_not_stalled_when_fresh(self):
        t = self._tracker(stall_after=300.0)
        now = time.time()
        t.record("etl", 100.0, now=now)
        result = t.evaluate("etl", now=now + 10)
        assert result is not None
        assert not result.stalled

    def test_stalled_when_old(self):
        t = self._tracker(stall_after=60.0)
        base = time.time()
        t.record("etl", 100.0, now=base)
        result = t.evaluate("etl", now=base + 120)
        assert result.stalled

    def test_not_regressed_when_advancing(self):
        t = self._tracker()
        base = time.time()
        t.record("etl", 50.0, now=base)
        t.record("etl", 100.0, now=base + 5)
        result = t.evaluate("etl", now=base + 10)
        assert not result.regressed

    def test_regressed_when_position_drops(self):
        t = self._tracker()
        base = time.time()
        t.record("etl", 100.0, now=base)
        t.record("etl", 80.0, now=base + 5)
        result = t.evaluate("etl", now=base + 10)
        assert result.regressed

    def test_last_position_is_previous_entry(self):
        t = self._tracker()
        base = time.time()
        t.record("etl", 10.0, now=base)
        t.record("etl", 20.0, now=base + 1)
        result = t.evaluate("etl", now=base + 2)
        assert result.last_position == 10.0
        assert result.current_position == 20.0

    def test_max_history_respected(self):
        t = CheckpointTracker(CheckpointConfig(max_history=5))
        base = time.time()
        for i in range(10):
            t.record("etl", float(i), now=base + i)
        # The tracker should not retain more entries than max_history
        assert len(t.history("etl")) <= 5

    def test_stall_exactly_at_boundary_is_not_stalled(self):
        """A recording exactly at the stall_after boundary should not be stalled."""
        t = self._tracker(stall_after=60.0)
        base = time.time()
        t.record("etl", 100.0, now=base)
        result = t.evaluate("etl", now=base + 60)
        assert not result.stalled

    def test_stall_just_past_boundary_is_stalled(self):
        """A recording just past the stall_after boundary should be stalled."""
        t = self._tracker(stall_after=60.0)
        base = time.time()
        t.record("etl", 100.0, now=base)
        result = t.evaluate("etl", now=base + 60.001)
        assert result.stalled
