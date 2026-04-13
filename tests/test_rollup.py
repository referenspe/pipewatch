"""Tests for pipewatch.rollup."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from pipewatch.rollup import MetricRollup, RollupConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_snapshot(value: float, ts: datetime):
    snap = MagicMock()
    snap.value = value
    snap.timestamp = ts
    return snap


def _make_history(snapshots):
    history = MagicMock()
    history.all = MagicMock(return_value=snapshots)
    return history


T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# RollupConfig
# ---------------------------------------------------------------------------

class TestRollupConfig:
    def test_defaults(self):
        cfg = RollupConfig()
        assert cfg.window_seconds == 300
        assert cfg.max_windows == 12

    def test_from_dict_custom(self):
        cfg = RollupConfig.from_dict({"window_seconds": 60, "max_windows": 5})
        assert cfg.window_seconds == 60
        assert cfg.max_windows == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = RollupConfig.from_dict({})
        assert cfg.window_seconds == 300

    def test_to_dict_round_trip(self):
        cfg = RollupConfig(window_seconds=120, max_windows=6)
        assert RollupConfig.from_dict(cfg.to_dict()).window_seconds == 120


# ---------------------------------------------------------------------------
# MetricRollup.rollup
# ---------------------------------------------------------------------------

class TestMetricRollup:
    def test_empty_history_returns_no_windows(self):
        rollup = MetricRollup()
        result = rollup.rollup(_make_history([]), "cpu")
        assert result.metric_key == "cpu"
        assert result.windows == []
        assert result.latest() is None

    def test_single_snapshot_produces_one_window(self):
        snap = _make_snapshot(42.0, T0)
        result = MetricRollup().rollup(_make_history([snap]), "cpu")
        assert len(result.windows) == 1
        assert result.windows[0].count == 1
        assert result.windows[0].mean == pytest.approx(42.0)

    def test_snapshots_in_same_window_are_merged(self):
        snaps = [
            _make_snapshot(10.0, T0),
            _make_snapshot(20.0, T0 + timedelta(seconds=60)),
            _make_snapshot(30.0, T0 + timedelta(seconds=120)),
        ]
        cfg = RollupConfig(window_seconds=300)
        result = MetricRollup(cfg).rollup(_make_history(snaps), "mem")
        assert len(result.windows) == 1
        assert result.windows[0].count == 3
        assert result.windows[0].mean == pytest.approx(20.0)
        assert result.windows[0].minimum == pytest.approx(10.0)
        assert result.windows[0].maximum == pytest.approx(30.0)

    def test_snapshots_in_different_windows(self):
        snaps = [
            _make_snapshot(1.0, T0),
            _make_snapshot(2.0, T0 + timedelta(seconds=310)),
        ]
        cfg = RollupConfig(window_seconds=300)
        result = MetricRollup(cfg).rollup(_make_history(snaps), "rps")
        assert len(result.windows) == 2

    def test_max_windows_limits_output(self):
        snaps = [
            _make_snapshot(float(i), T0 + timedelta(seconds=i * 310))
            for i in range(10)
        ]
        cfg = RollupConfig(window_seconds=300, max_windows=3)
        result = MetricRollup(cfg).rollup(_make_history(snaps), "lat")
        assert len(result.windows) <= 3

    def test_to_dict_contains_expected_keys(self):
        snap = _make_snapshot(5.0, T0)
        result = MetricRollup().rollup(_make_history([snap]), "x")
        d = result.windows[0].to_dict()
        for key in ("start", "end", "metric_key", "count", "mean", "min", "max"):
            assert key in d
