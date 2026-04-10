"""Tests for pipewatch.notifier."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewatch.alerts import AlertEvent
from pipewatch.metrics import MetricStatus, PipelineMetric
from pipewatch.notifier import Notifier, NotifierConfig
from pipewatch.watcher import WatchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metric(name: str, status: MetricStatus, value: float = 1.0) -> PipelineMetric:
    return PipelineMetric(name=name, value=value, status=status)


def _make_result(metrics: list[PipelineMetric], target: str = "pipe-a") -> WatchResult:
    return WatchResult(target_name=target, metrics=metrics)


def _make_channel() -> MagicMock:
    ch = MagicMock()
    ch.send = MagicMock()
    return ch


# ---------------------------------------------------------------------------
# NotifierConfig defaults
# ---------------------------------------------------------------------------

class TestNotifierConfig:
    def test_default_min_status_is_warning(self):
        cfg = NotifierConfig()
        assert cfg.min_status == MetricStatus.WARNING

    def test_default_deduplicate_is_true(self):
        cfg = NotifierConfig()
        assert cfg.deduplicate is True


# ---------------------------------------------------------------------------
# Notifier.notify_from_result
# ---------------------------------------------------------------------------

class TestNotifier:
    def test_dispatches_warning_event(self):
        ch = _make_channel()
        notifier = Notifier(channels=[ch])
        result = _make_result([_make_metric("lag", MetricStatus.WARNING)])
        count = notifier.notify_from_result(result)
        assert count == 1
        ch.send.assert_called_once()
        sent_event: AlertEvent = ch.send.call_args[0][0]
        assert sent_event.metric.name == "lag"

    def test_dispatches_critical_event(self):
        ch = _make_channel()
        notifier = Notifier(channels=[ch])
        result = _make_result([_make_metric("errors", MetricStatus.CRITICAL)])
        count = notifier.notify_from_result(result)
        assert count == 1

    def test_skips_ok_events_by_default(self):
        ch = _make_channel()
        notifier = Notifier(channels=[ch])
        result = _make_result([_make_metric("throughput", MetricStatus.OK)])
        count = notifier.notify_from_result(result)
        assert count == 0
        ch.send.assert_not_called()

    def test_deduplication_suppresses_repeat(self):
        ch = _make_channel()
        notifier = Notifier(channels=[ch])
        result = _make_result([_make_metric("lag", MetricStatus.WARNING)])
        notifier.notify_from_result(result)
        count2 = notifier.notify_from_result(result)
        assert count2 == 0
        assert ch.send.call_count == 1

    def test_deduplication_disabled_sends_every_time(self):
        ch = _make_channel()
        cfg = NotifierConfig(deduplicate=False)
        notifier = Notifier(channels=[ch], config=cfg)
        result = _make_result([_make_metric("lag", MetricStatus.WARNING)])
        notifier.notify_from_result(result)
        notifier.notify_from_result(result)
        assert ch.send.call_count == 2

    def test_channel_exception_does_not_propagate(self):
        ch = _make_channel()
        ch.send.side_effect = RuntimeError("boom")
        notifier = Notifier(channels=[ch])
        result = _make_result([_make_metric("lag", MetricStatus.CRITICAL)])
        # Should not raise
        notifier.notify_from_result(result)

    def test_add_channel_at_runtime(self):
        notifier = Notifier()
        ch = _make_channel()
        notifier.add_channel(ch)
        result = _make_result([_make_metric("lag", MetricStatus.WARNING)])
        notifier.notify_from_result(result)
        ch.send.assert_called_once()
