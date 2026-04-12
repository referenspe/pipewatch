"""Alert deduplication — suppress repeated alerts for the same metric/status pair."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from pipewatch.alerts import AlertEvent
from pipewatch.metrics import MetricStatus


@dataclass
class DeduplicatorConfig:
    """Configuration for the alert deduplicator."""

    # Minimum seconds that must pass before the same alert fires again.
    cooldown_seconds: float = 300.0

    @classmethod
    def from_dict(cls, data: dict) -> "DeduplicatorConfig":
        return cls(cooldown_seconds=float(data.get("cooldown_seconds", 300.0)))

    def to_dict(self) -> dict:
        return {"cooldown_seconds": self.cooldown_seconds}


# Key: (metric_key, MetricStatus)
_CacheKey = Tuple[str, MetricStatus]


@dataclass
class Deduplicator:
    """Suppresses duplicate AlertEvents within a configurable cooldown window."""

    config: DeduplicatorConfig = field(default_factory=DeduplicatorConfig)
    _last_seen: Dict[_CacheKey, float] = field(default_factory=dict, init=False, repr=False)

    def should_send(self, event: AlertEvent, *, _now: Optional[float] = None) -> bool:
        """Return True if *event* should be forwarded; False if it is a duplicate."""
        now = _now if _now is not None else time.monotonic()
        key: _CacheKey = (event.metric.key, event.metric.status)
        last = self._last_seen.get(key)
        if last is None or (now - last) >= self.config.cooldown_seconds:
            self._last_seen[key] = now
            return True
        return False

    def reset(self, metric_key: str, status: Optional[MetricStatus] = None) -> None:
        """Clear cooldown state for *metric_key* (optionally for a specific status)."""
        if status is not None:
            self._last_seen.pop((metric_key, status), None)
        else:
            for s in list(MetricStatus):
                self._last_seen.pop((metric_key, s), None)

    def clear(self) -> None:
        """Remove all cached state."""
        self._last_seen.clear()
