"""Tests for pipewatch.scheduler."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.alerts import AlertEvent, AlertChannel
from pipewatch.scheduler import Scheduler, SchedulerConfig
from pipewatch.watcher import PipelineWatcher, WatchResult, WatchTarget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_target(name: str = "pipe") -> WatchTarget:
    metric = PipelineMetric(
        name=name,
        value=5.0,
        threshold=ThresholdConfig(warning=3.0, critical=10.0),
    )
    return WatchTarget(name=name, fetch=lambda: metric)


def _make_alert_result(target_name: str = "pipe") -> WatchResult:
    metric = PipelineMetric(
        name=target_name,
        value=15.0,
        threshold=ThresholdConfig(warning=3.0, critical=10.0),
    )
    event = AlertEvent(metric=metric)
    return WatchResult(target_name=target_name, metric=metric, alert_events=[event])


def _make_ok_result(target_name: str = "pipe") -> WatchResult:
    metric = PipelineMetric(
        name=target_name,
        value=1.0,
        threshold=ThresholdConfig(warning=3.0, critical=10.0),
    )
    return WatchResult(target_name=target_name, metric=metric, alert_events=[])


# ---------------------------------------------------------------------------
# SchedulerConfig
# ---------------------------------------------------------------------------

class TestSchedulerConfig:
    def test_defaults(self):
        cfg = SchedulerConfig()
        assert cfg.interval_seconds == 60.0
        assert cfg.max_iterations is None

    def test_custom_values(self):
        cfg = SchedulerConfig(interval_seconds=5.0, max_iterations=3)
        assert cfg.interval_seconds == 5.0
        assert cfg.max_iterations == 3


# ---------------------------------------------------------------------------
# Scheduler.run_once
# ---------------------------------------------------------------------------

class TestSchedulerRunOnce:
    def _make_scheduler(self, run_result: WatchResult) -> tuple[Scheduler, MagicMock]:
        watcher = MagicMock(spec=PipelineWatcher)
        watcher.targets = [_make_target()]
        watcher.run.return_value = run_result

        channel = MagicMock(spec=AlertChannel)
        scheduler = Scheduler(
            watcher=watcher,
            channels=[channel],
            config=SchedulerConfig(interval_seconds=1.0),
        )
        return scheduler, channel

    def test_returns_report(self):
        scheduler, _ = self._make_scheduler(_make_ok_result())
        report = scheduler.run_once()
        assert report is not None
        assert len(report.results) == 1

    def test_sends_alert_when_triggered(self):
        alert_result = _make_alert_result()
        scheduler, channel = self._make_scheduler(alert_result)
        scheduler.run_once()
        channel.send.assert_called_once()

    def test_no_alert_when_ok(self):
        scheduler, channel = self._make_scheduler(_make_ok_result())
        scheduler.run_once()
        channel.send.assert_not_called()

    def test_channel_error_does_not_raise(self):
        alert_result = _make_alert_result()
        scheduler, channel = self._make_scheduler(alert_result)
        channel.send.side_effect = RuntimeError("network down")
        # Should not propagate
        scheduler.run_once()


# ---------------------------------------------------------------------------
# Scheduler.start
# ---------------------------------------------------------------------------

class TestSchedulerStart:
    def test_respects_max_iterations(self):
        watcher = MagicMock(spec=PipelineWatcher)
        watcher.targets = [_make_target()]
        watcher.run.return_value = _make_ok_result()

        scheduler = Scheduler(
            watcher=watcher,
            channels=[],
            config=SchedulerConfig(interval_seconds=0.0, max_iterations=3),
        )
        sleep_mock = MagicMock()
        scheduler.start(sleep_fn=sleep_mock)

        assert scheduler._iteration_count == 3
        assert sleep_mock.call_count == 2  # sleeps between iterations, not after last
