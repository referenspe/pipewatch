"""Escalation policy: promote alert severity after repeated firing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from pipewatch.metrics import MetricStatus


@dataclass
class EscalationPolicy:
    """Configuration for escalation behaviour."""
    escalate_after: int = 3          # consecutive alert count before escalating
    escalation_window: int = 300     # seconds — resets counter if gap exceeds this
    max_level: MetricStatus = MetricStatus.CRITICAL

    @classmethod
    def from_dict(cls, data: dict) -> "EscalationPolicy":
        return cls(
            escalate_after=data.get("escalate_after", 3),
            escalation_window=data.get("escalation_window", 300),
            max_level=MetricStatus[data.get("max_level", "CRITICAL").upper()],
        )

    def to_dict(self) -> dict:
        return {
            "escalate_after": self.escalate_after,
            "escalation_window": self.escalation_window,
            "max_level": self.max_level.name,
        }


@dataclass
class _EscalationState:
    count: int = 0
    last_seen: Optional[datetime] = None
    escalated: bool = False


@dataclass
class EscalationResult:
    metric_key: str
    original_status: MetricStatus
    effective_status: MetricStatus
    consecutive_count: int
    escalated: bool

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "original_status": self.original_status.name,
            "effective_status": self.effective_status.name,
            "consecutive_count": self.consecutive_count,
            "escalated": self.escalated,
        }


class EscalationTracker:
    """Tracks consecutive alert firings per metric and escalates when warranted."""

    def __init__(self, policy: Optional[EscalationPolicy] = None) -> None:
        self._policy = policy or EscalationPolicy()
        self._states: Dict[str, _EscalationState] = {}

    def evaluate(
        self,
        metric_key: str,
        status: MetricStatus,
        now: Optional[datetime] = None,
    ) -> EscalationResult:
        now = now or datetime.utcnow()
        state = self._states.setdefault(metric_key, _EscalationState())
        window = timedelta(seconds=self._policy.escalation_window)

        is_alert = status in (MetricStatus.WARNING, MetricStatus.CRITICAL)

        if not is_alert:
            # Clear state on recovery
            self._states[metric_key] = _EscalationState()
            return EscalationResult(metric_key, status, status, 0, False)

        # Reset if gap exceeds window
        if state.last_seen and (now - state.last_seen) > window:
            state.count = 0
            state.escalated = False

        state.count += 1
        state.last_seen = now

        should_escalate = state.count >= self._policy.escalate_after
        effective = self._policy.max_level if should_escalate else status
        state.escalated = should_escalate

        return EscalationResult(
            metric_key=metric_key,
            original_status=status,
            effective_status=effective,
            consecutive_count=state.count,
            escalated=should_escalate,
        )

    def reset(self, metric_key: str) -> None:
        self._states.pop(metric_key, None)
