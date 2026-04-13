"""Watchdog module: detects stale metrics that have not been updated within a deadline."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class WatchdogConfig:
    """Configuration for the watchdog checker."""

    stale_after_seconds: float = 60.0
    critical_after_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if self.critical_after_seconds <= self.stale_after_seconds:
            raise ValueError(
                "critical_after_seconds must be greater than stale_after_seconds"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "WatchdogConfig":
        return cls(
            stale_after_seconds=float(data.get("stale_after_seconds", 60.0)),
            critical_after_seconds=float(data.get("critical_after_seconds", 300.0)),
        )

    def to_dict(self) -> dict:
        return {
            "stale_after_seconds": self.stale_after_seconds,
            "critical_after_seconds": self.critical_after_seconds,
        }


@dataclass
class WatchdogResult:
    """Result of a watchdog staleness check for a single metric key."""

    metric_key: str
    last_seen: Optional[float]  # epoch seconds, or None if never seen
    age_seconds: float
    is_stale: bool
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "last_seen": self.last_seen,
            "age_seconds": round(self.age_seconds, 3),
            "is_stale": self.is_stale,
            "is_critical": self.is_critical,
        }


class Watchdog:
    """Tracks last-seen timestamps and reports stale metrics."""

    def __init__(self, config: Optional[WatchdogConfig] = None) -> None:
        self._config = config or WatchdogConfig()
        self._last_seen: Dict[str, float] = {}

    def touch(self, metric_key: str, ts: Optional[float] = None) -> None:
        """Record that *metric_key* was observed at *ts* (defaults to now)."""
        self._last_seen[metric_key] = ts if ts is not None else time.time()

    def check(self, metric_key: str, now: Optional[float] = None) -> WatchdogResult:
        """Return a WatchdogResult describing the staleness of *metric_key*."""
        now = now if now is not None else time.time()
        last = self._last_seen.get(metric_key)
        age = (now - last) if last is not None else float("inf")
        return WatchdogResult(
            metric_key=metric_key,
            last_seen=last,
            age_seconds=age,
            is_stale=age >= self._config.stale_after_seconds,
            is_critical=age >= self._config.critical_after_seconds,
        )

    def check_all(self, now: Optional[float] = None) -> Dict[str, WatchdogResult]:
        """Check all tracked metric keys and return a mapping of results."""
        return {key: self.check(key, now=now) for key in self._last_seen}
