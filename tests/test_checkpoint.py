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
        t = CheckpointTracker(CheckpointConfig(max_history=3))
        for i in range(10):
            t.record("s", float(i))
        assert len(t._history["s"]) == 3

    def test_stages_lists_recorded_stages(self):
        t = self._tracker()
        t.record("a", 1.0)
        t.record("b", 2.0)
        assert set(t.stages()) == {"a", "b"}

    def test_to_dict_has_expected_keys(self):
        t = self._tracker(stall_after=30.0)
        base = time.time()
        t.record("x", 5.0, now=base)
        result = t.evaluate("x", now=base + 1)
        d = result.to_dict()
        assert "stalled" in d
        assert "regressed" in d
        assert "seconds_since_update" in d
