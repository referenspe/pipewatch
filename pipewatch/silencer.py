"""Silencer: suppress alerts for specific metrics during maintenance windows."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SilenceRule:
    """A rule that suppresses alerts for a metric key for a fixed duration."""

    metric_key: str
    expires_at: float  # Unix timestamp
    reason: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        """Return True if the silence window is still in effect."""
        now = now if now is not None else time.time()
        return now < self.expires_at

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "expires_at": self.expires_at,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SilenceRule":
        return cls(
            metric_key=data["metric_key"],
            expires_at=float(data["expires_at"]),
            reason=data.get("reason", ""),
        )


@dataclass
class Silencer:
    """Manages a collection of silence rules for pipeline metrics."""

    _rules: Dict[str, List[SilenceRule]] = field(default_factory=dict, init=False)

    def silence(self, metric_key: str, duration_seconds: float, reason: str = "") -> SilenceRule:
        """Add a silence rule for *metric_key* lasting *duration_seconds* from now."""
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        rule = SilenceRule(
            metric_key=metric_key,
            expires_at=time.time() + duration_seconds,
            reason=reason,
        )
        self._rules.setdefault(metric_key, []).append(rule)
        return rule

    def is_silenced(self, metric_key: str, now: Optional[float] = None) -> bool:
        """Return True if *metric_key* has at least one active silence rule."""
        now = now if now is not None else time.time()
        rules = self._rules.get(metric_key, [])
        return any(r.is_active(now) for r in rules)

    def prune(self, now: Optional[float] = None) -> int:
        """Remove expired rules and return the count of removed entries."""
        now = now if now is not None else time.time()
        removed = 0
        for key in list(self._rules):
            before = len(self._rules[key])
            self._rules[key] = [r for r in self._rules[key] if r.is_active(now)]
            removed += before - len(self._rules[key])
            if not self._rules[key]:
                del self._rules[key]
        return removed

    def active_rules(self, now: Optional[float] = None) -> List[SilenceRule]:
        """Return all currently active silence rules across all metric keys."""
        now = now if now is not None else time.time()
        return [r for rules in self._rules.values() for r in rules if r.is_active(now)]
