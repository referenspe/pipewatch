"""Heartbeat tracker — detects when a pipeline stops reporting metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat monitoring."""

    timeout_seconds: float = 60.0
    critical_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.critical_seconds <= self.timeout_seconds:
            raise ValueError("critical_seconds must be greater than timeout_seconds")

    @classmethod
    def from_dict(cls, data: dict) -> "HeartbeatConfig":
        return cls(
            timeout_seconds=float(data.get("timeout_seconds", 60.0)),
            critical_seconds=float(data.get("critical_seconds", 300.0)),
        )

    def to_dict(self) -> dict:
        return {
            "timeout_seconds": self.timeout_seconds,
            "critical_seconds": self.critical_seconds,
        }


@dataclass
class HeartbeatResult:
    """Result of a heartbeat check for a single pipeline key."""

    key: str
    last_seen: Optional[datetime]
    elapsed_seconds: Optional[float]
    is_stale: bool
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "elapsed_seconds": self.elapsed_seconds,
            "is_stale": self.is_stale,
            "is_critical": self.is_critical,
        }


class HeartbeatTracker:
    """Tracks last-seen timestamps and evaluates staleness."""

    def __init__(self, config: HeartbeatConfig) -> None:
        self._config = config
        self._registry: Dict[str, datetime] = {}

    def ping(self, key: str, now: Optional[datetime] = None) -> None:
        """Record a heartbeat for *key* at *now* (defaults to UTC now)."""
        self._registry[key] = now or datetime.now(timezone.utc)

    def check(self, key: str, now: Optional[datetime] = None) -> HeartbeatResult:
        """Evaluate whether *key* is stale or critical."""
        now = now or datetime.now(timezone.utc)
        last_seen = self._registry.get(key)

        if last_seen is None:
            return HeartbeatResult(
                key=key,
                last_seen=None,
                elapsed_seconds=None,
                is_stale=True,
                is_critical=True,
            )

        elapsed = (now - last_seen).total_seconds()
        return HeartbeatResult(
            key=key,
            last_seen=last_seen,
            elapsed_seconds=elapsed,
            is_stale=elapsed >= self._config.timeout_seconds,
            is_critical=elapsed >= self._config.critical_seconds,
        )

    def check_all(self, now: Optional[datetime] = None) -> list[HeartbeatResult]:
        """Check every registered key."""
        now = now or datetime.now(timezone.utc)
        return [self.check(key, now) for key in self._registry]

    def known_keys(self) -> list[str]:
        return list(self._registry.keys())
