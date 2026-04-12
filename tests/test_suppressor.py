"""Tests for pipewatch.suppressor."""

from datetime import datetime, timedelta

import pytest

from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.alerts import AlertEvent
from pipewatch.suppressor import Suppressor, SuppressorConfig


def _make_metric(key: str = "latency", status: MetricStatus = MetricStatus.WARNING) -> PipelineMetric:
    thresholds = ThresholdConfig(warning=50.0, critical=100.0)
    return PipelineMetric(key=key, value=75.0, status=status, thresholds=thresholds)


def _make_event(key: str = "latency", status: MetricStatus = MetricStatus.WARNING) -> AlertEvent:
    return AlertEvent(metric=_make_metric(key, status))


class TestSuppressorConfig:
    def test_defaults(self):
        cfg = SuppressorConfig()
        assert cfg.window_seconds == 300
        assert cfg.max_suppressed == 10

    def test_from_dict_custom(self):
        cfg = SuppressorConfig.from_dict({"window_seconds": 60, "max_suppressed": 3})
        assert cfg.window_seconds == 60
        assert cfg.max_suppressed == 3

    def test_from_dict_defaults_when_missing(self):
        cfg = SuppressorConfig.from_dict({})
        assert cfg.window_seconds == 300
        assert cfg.max_suppressed == 10

    def test_to_dict_round_trip(self):
        cfg = SuppressorConfig(window_seconds=120, max_suppressed=5)
        assert SuppressorConfig.from_dict(cfg.to_dict()) == cfg


class TestSuppressor:
    def test_first_event_not_suppressed(self):
        s = Suppressor()
        result = s.evaluate(_make_event())
        assert result.suppressed is False

    def test_second_event_within_window_suppressed(self):
        s = Suppressor(SuppressorConfig(window_seconds=300))
        now = datetime.utcnow()
        s.evaluate(_make_event(), now=now)
        result = s.evaluate(_make_event(), now=now + timedelta(seconds=10))
        assert result.suppressed is True
        assert result.suppressed_count == 1

    def test_event_after_window_not_suppressed(self):
        s = Suppressor(SuppressorConfig(window_seconds=60))
        now = datetime.utcnow()
        s.evaluate(_make_event(), now=now)
        result = s.evaluate(_make_event(), now=now + timedelta(seconds=61))
        assert result.suppressed is False

    def test_force_through_after_max_suppressed(self):
        s = Suppressor(SuppressorConfig(window_seconds=300, max_suppressed=2))
        now = datetime.utcnow()
        s.evaluate(_make_event(), now=now)
        s.evaluate(_make_event(), now=now + timedelta(seconds=1))
        s.evaluate(_make_event(), now=now + timedelta(seconds=2))
        result = s.evaluate(_make_event(), now=now + timedelta(seconds=3))
        assert result.suppressed is False

    def test_different_keys_tracked_independently(self):
        s = Suppressor()
        now = datetime.utcnow()
        s.evaluate(_make_event(key="latency"), now=now)
        result = s.evaluate(_make_event(key="error_rate"), now=now + timedelta(seconds=1))
        assert result.suppressed is False

    def test_different_statuses_tracked_independently(self):
        s = Suppressor()
        now = datetime.utcnow()
        s.evaluate(_make_event(status=MetricStatus.WARNING), now=now)
        result = s.evaluate(_make_event(status=MetricStatus.CRITICAL), now=now + timedelta(seconds=1))
        assert result.suppressed is False

    def test_reset_clears_state(self):
        s = Suppressor()
        now = datetime.utcnow()
        s.evaluate(_make_event(), now=now)
        s.reset()
        result = s.evaluate(_make_event(), now=now + timedelta(seconds=1))
        assert result.suppressed is False

    def test_suppress_result_str_suppressed(self):
        s = Suppressor(SuppressorConfig(window_seconds=300))
        now = datetime.utcnow()
        s.evaluate(_make_event(), now=now)
        result = s.evaluate(_make_event(), now=now + timedelta(seconds=5))
        assert "SUPPRESSED" in str(result)

    def test_suppress_result_str_not_suppressed(self):
        s = Suppressor()
        result = s.evaluate(_make_event())
        assert "SUPPRESSED" not in str(result)
