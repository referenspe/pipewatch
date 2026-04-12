"""Tests for pipewatch.replay."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.metrics import MetricStatus, ThresholdConfig
from pipewatch.replay import ReplayConfig, ReplayEngine, ReplayResult


def _make_history(values):
    history = MetricHistory()
    base = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    for i, v in enumerate(values):
        snap = MetricSnapshot(
            key="cpu",
            value=v,
            timestamp=base + datetime.timedelta(minutes=i),
        )
        history._store.setdefault("cpu", []).append(snap)
    return history


class TestReplayConfig:
    def test_defaults(self):
        cfg = ReplayConfig()
        assert cfg.max_snapshots == 500
        assert cfg.stop_on_critical is False

    def test_from_dict_custom(self):
        cfg = ReplayConfig.from_dict({"max_snapshots": 10, "stop_on_critical": True})
        assert cfg.max_snapshots == 10
        assert cfg.stop_on_critical is True

    def test_to_dict_round_trip(self):
        cfg = ReplayConfig(max_snapshots=50, stop_on_critical=True)
        assert ReplayConfig.from_dict(cfg.to_dict()) == cfg


class TestReplayEngine:
    def _threshold(self):
        return ThresholdConfig(warning=70.0, critical=90.0)

    def test_all_ok_below_warning(self):
        history = _make_history([10.0, 20.0, 30.0])
        engine = ReplayEngine()
        result = engine.run("cpu", history, self._threshold())
        assert result.total == 3
        assert result.critical_count == 0
        assert result.warning_count == 0
        assert result.stopped_early is False

    def test_counts_warnings(self):
        history = _make_history([10.0, 75.0, 80.0])
        engine = ReplayEngine()
        result = engine.run("cpu", history, self._threshold())
        assert result.warning_count == 2

    def test_counts_criticals(self):
        history = _make_history([10.0, 95.0, 92.0])
        engine = ReplayEngine()
        result = engine.run("cpu", history, self._threshold())
        assert result.critical_count == 2

    def test_stop_on_critical(self):
        history = _make_history([10.0, 95.0, 20.0, 30.0])
        cfg = ReplayConfig(stop_on_critical=True)
        engine = ReplayEngine(config=cfg)
        result = engine.run("cpu", history, self._threshold())
        assert result.stopped_early is True
        assert result.total == 2

    def test_respects_max_snapshots(self):
        history = _make_history(list(range(20)))
        cfg = ReplayConfig(max_snapshots=5)
        engine = ReplayEngine(config=cfg)
        result = engine.run("cpu", history, self._threshold())
        assert result.total == 5

    def test_empty_history_returns_zero_total(self):
        history = MetricHistory()
        engine = ReplayEngine()
        result = engine.run("cpu", history, self._threshold())
        assert result.total == 0

    def test_to_dict_contains_key(self):
        history = _make_history([10.0])
        engine = ReplayEngine()
        result = engine.run("cpu", history, self._threshold())
        d = result.to_dict()
        assert d["key"] == "cpu"
        assert "events" in d
