"""Alert throttling: suppress repeated alerts for the same metric within a time window."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleConfig:
    """Configuration for the alert throttler."""
    window_seconds: float = 300.0  # 5 minutes default
    max_alerts_per_window: int = 3

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleConfig":
        return cls(
            window_seconds=float(data.get("window_seconds", 300.0)),
            max_alerts_per_window=int(data.get("max_alerts_per_window", 3)),
        )

    def to_dict(self) -> dict:
        return {
            "window_seconds": self.window_seconds,
            "max_alerts_per_window": self.max_alerts_per_window,
        }


@dataclass
 class _MetricWindow:
    timestamps: list = field(default_factory=list)

    def prune(self, cutoff: float) -> None:
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count(self) -> int:
        return len(self.timestamps)

    def record(self, ts: float) -> None:
        self.timestamps.append(ts)


class AlertThrottler:
    """Tracks alert frequency per metric key and suppresses excess alerts."""

    def __init__(self, config: Optional[ThrottleConfig] = None) -> None:
        self._config = config or ThrottleConfig()
        self._windows: Dict[str, _MetricWindow] = {}

    def _window(self, key: str) -> _MetricWindow:
        if key not in self._windows:
            self._windows[key] = _MetricWindow()
        return self._windows[key]

    def should_send(self, metric_key: str, now: Optional[float] = None) -> bool:
        """Return True if the alert should be sent, False if throttled."""
        ts = now if now is not None else time.monotonic()
        cutoff = ts - self._config.window_seconds
        win = self._window(metric_key)
        win.prune(cutoff)
        if win.count() < self._config.max_alerts_per_window:
            win.record(ts)
            return True
        return False

    def reset(self, metric_key: str) -> None:
        """Clear the tracking window for a given metric key."""
        self._windows.pop(metric_key, None)

    def stats(self, metric_key: str, now: Optional[float] = None) -> dict:
        """Return current window stats for a metric key."""
        ts = now if now is not None else time.monotonic()
        cutoff = ts - self._config.window_seconds
        win = self._window(metric_key)
        win.prune(cutoff)
        return {
            "metric_key": metric_key,
            "alerts_in_window": win.count(),
            "max_alerts_per_window": self._config.max_alerts_per_window,
            "window_seconds": self._config.window_seconds,
        }
