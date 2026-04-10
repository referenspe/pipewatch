"""Tests for pipewatch.alerts module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewatch.alerts import AlertDispatcher, AlertEvent, AlertChannel, LoggingChannel
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig, evaluate


def _make_metric(value: float, warning: float = 50.0, critical: float = 80.0) -> PipelineMetric:
    config = ThresholdConfig(warning=warning, critical=critical)
    return evaluate("test_metric", value, config)


# ---------------------------------------------------------------------------
# AlertEvent
# ---------------------------------------------------------------------------

class TestAlertEvent:
    def test_str_contains_metric_name(self):
        m = _make_metric(90.0)
        event = AlertEvent(metric_name=m.name, status=m.status, value=m.value, message="msg")
        assert "test_metric" in str(event)

    def test_str_contains_status(self):
        m = _make_metric(90.0)
        event = AlertEvent(metric_name=m.name, status=m.status, value=m.value, message="msg")
        assert "critical" in str(event).lower()


# ---------------------------------------------------------------------------
# LoggingChannel
# ---------------------------------------------------------------------------

class TestLoggingChannel:
    def test_send_warning_logs_at_warning_level(self, caplog):
        import logging
        channel = LoggingChannel()
        m = _make_metric(60.0)
        event = AlertEvent(metric_name=m.name, status=m.status, value=m.value, message="warn")
        with caplog.at_level(logging.WARNING, logger="pipewatch.alerts"):
            channel.send(event)
        assert any("test_metric" in r.message for r in caplog.records)

    def test_send_critical_logs_at_critical_level(self, caplog):
        import logging
        channel = LoggingChannel()
        m = _make_metric(90.0)
        event = AlertEvent(metric_name=m.name, status=m.status, value=m.value, message="crit")
        with caplog.at_level(logging.CRITICAL, logger="pipewatch.alerts"):
            channel.send(event)
        assert any(r.levelno == logging.CRITICAL for r in caplog.records)


# ---------------------------------------------------------------------------
# AlertDispatcher
# ---------------------------------------------------------------------------

class TestAlertDispatcher:
    def test_no_event_for_ok_metric(self):
        dispatcher = AlertDispatcher()
        m = _make_metric(10.0)
        assert dispatcher.dispatch(m) is None

    def test_event_returned_for_warning(self):
        dispatcher = AlertDispatcher()
        m = _make_metric(60.0)
        event = dispatcher.dispatch(m)
        assert event is not None
        assert event.status == MetricStatus.WARNING

    def test_event_returned_for_critical(self):
        dispatcher = AlertDispatcher()
        m = _make_metric(90.0)
        event = dispatcher.dispatch(m)
        assert event is not None
        assert event.status == MetricStatus.CRITICAL

    def test_all_channels_called(self):
        ch1 = MagicMock(spec=AlertChannel)
        ch2 = MagicMock(spec=AlertChannel)
        dispatcher = AlertDispatcher(channels=[ch1, ch2])
        m = _make_metric(90.0)
        dispatcher.dispatch(m)
        ch1.send.assert_called_once()
        ch2.send.assert_called_once()

    def test_channel_failure_does_not_raise(self):
        ch = MagicMock(spec=AlertChannel)
        ch.name = "broken"
        ch.send.side_effect = RuntimeError("boom")
        dispatcher = AlertDispatcher(channels=[ch])
        m = _make_metric(90.0)
        # Should not raise
        dispatcher.dispatch(m)

    def test_add_channel(self):
        dispatcher = AlertDispatcher()
        ch = MagicMock(spec=AlertChannel)
        dispatcher.add_channel(ch)
        m = _make_metric(90.0)
        dispatcher.dispatch(m)
        ch.send.assert_called_once()
