"""Quota tracking — enforce per-key event/metric count limits within a window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class QuotaConfig:
    window_seconds: int = 60
    max_events: int = 100

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_events < 1:
            raise ValueError("max_events must be at least 1")

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaConfig":
        return cls(
            window_seconds=data.get("window_seconds", 60),
            max_events=data.get("max_events", 100),
        )

    def to_dict(self) -> dict:
        return {"window_seconds": self.window_seconds, "max_events": self.max_events}


@dataclass
class QuotaResult:
    key: str
    allowed: bool
    current_count: int
    limit: int
    window_seconds: int

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "allowed": self.allowed,
            "current_count": self.current_count,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
        }


@dataclass
class _KeyBucket:
    timestamps: list = field(default_factory=list)


class QuotaEnforcer:
    """Track per-key event counts within a rolling time window."""

    def __init__(self, config: Optional[QuotaConfig] = None) -> None:
        self._config = config or QuotaConfig()
        self._buckets: Dict[str, _KeyBucket] = {}

    def _prune(self, bucket: _KeyBucket, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        bucket.timestamps = [t for t in bucket.timestamps if t > cutoff]

    def check(self, key: str, now: Optional[datetime] = None) -> QuotaResult:
        """Record an event for *key* and return whether it is within quota."""
        now = now or datetime.utcnow()
        bucket = self._buckets.setdefault(key, _KeyBucket())
        self._prune(bucket, now)
        allowed = len(bucket.timestamps) < self._config.max_events
        if allowed:
            bucket.timestamps.append(now)
        return QuotaResult(
            key=key,
            allowed=allowed,
            current_count=len(bucket.timestamps),
            limit=self._config.max_events,
            window_seconds=self._config.window_seconds,
        )

    def reset(self, key: str) -> None:
        """Clear quota state for *key*."""
        self._buckets.pop(key, None)

    def usage(self, key: str, now: Optional[datetime] = None) -> int:
        """Return current event count for *key* within the window."""
        now = now or datetime.utcnow()
        bucket = self._buckets.get(key)
        if bucket is None:
            return 0
        self._prune(bucket, now)
        return len(bucket.timestamps)
