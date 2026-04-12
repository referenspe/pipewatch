"""Tests for pipewatch.deduplicator."""
from __future__ import annotations

import pytest

from pipewatch.alerts import AlertEvent
from pipewatch.deduplicator import Deduplicator, DeduplicatorConfig
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


def _make_event(key: str = "cpu", status: MetricStatus = MetricStatus.CRITICAL) -> AlertEvent:
    thresholds = ThresholdConfig(warning=70.0, critical=90.0)
    metric = PipelineMetric(key=key, value=95.0, thresholds=thresholds, status=status)
    return AlertEvent(metric=metric, message=f"{key} is {status.value}")


# ---------------------------------------------------------------------------
# DeduplicatorConfig
# ---------------------------------------------------------------------------

class TestDeduplicatorConfig:
    def test_default_cooldown(self):
        cfg = DeduplicatorConfig()
        assert cfg.cooldown_seconds == 300.0

    def test_from_dict_custom(self):
        cfg = DeduplicatorConfig.from_dict({"cooldown_seconds": 60})
        assert cfg.cooldown_seconds == 60.0

    def test_from_dict_default_when_missing(self):
        cfg = DeduplicatorConfig.from_dict({})
        assert cfg.cooldown_seconds == 300.0

    def test_to_dict_round_trip(self):
        cfg = DeduplicatorConfig(cooldown_seconds=120.0)
        assert DeduplicatorConfig.from_dict(cfg.to_dict()).cooldown_seconds == 120.0


# ---------------------------------------------------------------------------
# Deduplicator.should_send
# ---------------------------------------------------------------------------

class TestDeduplicatorShouldSend:
    def test_first_event_is_allowed(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=60.0))
        assert d.should_send(_make_event(), _now=0.0) is True

    def test_immediate_repeat_is_suppressed(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=60.0))
        d.should_send(_make_event(), _now=0.0)
        assert d.should_send(_make_event(), _now=30.0) is False

    def test_allowed_after_cooldown_expires(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=60.0))
        d.should_send(_make_event(), _now=0.0)
        assert d.should_send(_make_event(), _now=60.0) is True

    def test_different_status_is_independent(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=60.0))
        warn_event = _make_event(status=MetricStatus.WARNING)
        crit_event = _make_event(status=MetricStatus.CRITICAL)
        d.should_send(warn_event, _now=0.0)
        assert d.should_send(crit_event, _now=1.0) is True

    def test_different_metric_key_is_independent(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=60.0))
        d.should_send(_make_event(key="cpu"), _now=0.0)
        assert d.should_send(_make_event(key="mem"), _now=1.0) is True


# ---------------------------------------------------------------------------
# Deduplicator.reset / clear
# ---------------------------------------------------------------------------

class TestDeduplicatorReset:
    def test_reset_specific_status_allows_resend(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=300.0))
        event = _make_event(key="cpu", status=MetricStatus.CRITICAL)
        d.should_send(event, _now=0.0)
        d.reset("cpu", MetricStatus.CRITICAL)
        assert d.should_send(event, _now=1.0) is True

    def test_reset_all_statuses_for_key(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=300.0))
        d.should_send(_make_event(key="cpu", status=MetricStatus.WARNING), _now=0.0)
        d.should_send(_make_event(key="cpu", status=MetricStatus.CRITICAL), _now=0.0)
        d.reset("cpu")
        assert d.should_send(_make_event(key="cpu", status=MetricStatus.WARNING), _now=1.0) is True
        assert d.should_send(_make_event(key="cpu", status=MetricStatus.CRITICAL), _now=1.0) is True

    def test_clear_removes_all_state(self):
        d = Deduplicator(config=DeduplicatorConfig(cooldown_seconds=300.0))
        d.should_send(_make_event(key="cpu"), _now=0.0)
        d.should_send(_make_event(key="mem"), _now=0.0)
        d.clear()
        assert d.should_send(_make_event(key="cpu"), _now=1.0) is True
