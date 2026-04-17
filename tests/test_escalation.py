"""Tests for pipewatch.escalation."""
from datetime import datetime, timedelta

import pytest

from pipewatch.escalation import EscalationPolicy, EscalationTracker
from pipewatch.metrics import MetricStatus


# ---------------------------------------------------------------------------
# EscalationPolicy
# ---------------------------------------------------------------------------

class TestEscalationPolicy:
    def test_defaults(self):
        p = EscalationPolicy()
        assert p.escalate_after == 3
        assert p.escalation_window == 300
        assert p.max_level == MetricStatus.CRITICAL

    def test_from_dict_custom(self):
        p = EscalationPolicy.from_dict({"escalate_after": 2, "escalation_window": 60, "max_level": "CRITICAL"})
        assert p.escalate_after == 2
        assert p.escalation_window == 60

    def test_from_dict_defaults_when_missing(self):
        p = EscalationPolicy.from_dict({})
        assert p.escalate_after == 3

    def test_to_dict_round_trip(self):
        p = EscalationPolicy(escalate_after=5, escalation_window=120)
        assert EscalationPolicy.from_dict(p.to_dict()).escalate_after == 5


# ---------------------------------------------------------------------------
# EscalationTracker
# ---------------------------------------------------------------------------

_T0 = datetime(2024, 1, 1, 12, 0, 0)


def _tick(base: datetime, seconds: int) -> datetime:
    return base + timedelta(seconds=seconds)


class TestEscalationTracker:
    def _tracker(self, escalate_after: int = 3, window: int = 300) -> EscalationTracker:
        policy = EscalationPolicy(escalate_after=escalate_after, escalation_window=window)
        return EscalationTracker(policy)

    def test_ok_status_not_escalated(self):
        tracker = self._tracker()
        result = tracker.evaluate("cpu", MetricStatus.OK, now=_T0)
        assert result.effective_status == MetricStatus.OK
        assert not result.escalated

    def test_single_warning_not_escalated(self):
        tracker = self._tracker(escalate_after=3)
        result = tracker.evaluate("cpu", MetricStatus.WARNING, now=_T0)
        assert result.effective_status == MetricStatus.WARNING
        assert not result.escalated
        assert result.consecutive_count == 1

    def test_escalates_after_threshold(self):
        tracker = self._tracker(escalate_after=3)
        for i in range(2):
            tracker.evaluate("cpu", MetricStatus.WARNING, now=_tick(_T0, i * 10))
        result = tracker.evaluate("cpu", MetricStatus.WARNING, now=_tick(_T0, 20))
        assert result.escalated
        assert result.effective_status == MetricStatus.CRITICAL
        assert result.consecutive_count == 3

    def test_recovery_resets_count(self):
        tracker = self._tracker(escalate_after=2)
        tracker.evaluate("cpu", MetricStatus.WARNING, now=_T0)
        tracker.evaluate("cpu", MetricStatus.WARNING, now=_tick(_T0, 10))
        tracker.evaluate("cpu", MetricStatus.OK, now=_tick(_T0, 20))
        result = tracker.evaluate("cpu", MetricStatus.WARNING, now=_tick(_T0, 30))
        assert not result.escalated
        assert result.consecutive_count == 1

    def test_window_expiry_resets_count(self):
        """Violations outside the escalation window should not count toward escalation."""
        tracker = self._tracker(escalate_after=2, window=60)
        tracker.evaluate("cpu", MetricStatus.WARNING, now=_T0)
        # Second violation arrives after the window has expired
        result = tracker.evaluate("cpu", MetricStatus.WARNING, now=_tick(_T0, 120))
        assert not result.escalated
        assert result.consecutive_count == 1
