"""Alert budget tracking: limits how many alerts fire in a rolling window."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, Optional


@dataclass
class BudgetConfig:
    max_alerts: int = 20
    window_seconds: int = 3600  # 1 hour
    per_key: bool = False  # if True, budget is tracked per metric key

    @classmethod
    def from_dict(cls, data: dict) -> "BudgetConfig":
        return cls(
            max_alerts=data.get("max_alerts", 20),
            window_seconds=data.get("window_seconds", 3600),
            per_key=data.get("per_key", False),
        )

    def to_dict(self) -> dict:
        return {
            "max_alerts": self.max_alerts,
            "window_seconds": self.window_seconds,
            "per_key": self.per_key,
        }


@dataclass
class BudgetResult:
    allowed: bool
    key: str
    used: int
    limit: int
    window_seconds: int

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "key": self.key,
            "used": self.used,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
        }


@dataclass
class _KeyBucket:
    timestamps: Deque[datetime] = field(default_factory=deque)


class AlertBudget:
    """Tracks alert counts within a rolling time window."""

    def __init__(self, config: Optional[BudgetConfig] = None) -> None:
        self._config = config or BudgetConfig()
        self._buckets: Dict[str, _KeyBucket] = {}

    def _bucket_for(self, key: str) -> _KeyBucket:
        if key not in self._buckets:
            self._buckets[key] = _KeyBucket()
        return self._buckets[key]

    def _prune(self, bucket: _KeyBucket, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        while bucket.timestamps and bucket.timestamps[0] < cutoff:
            bucket.timestamps.popleft()

    def check(self, metric_key: str, now: Optional[datetime] = None) -> BudgetResult:
        """Return BudgetResult; does NOT consume budget."""
        now = now or datetime.utcnow()
        key = metric_key if self._config.per_key else "__global__"
        bucket = self._bucket_for(key)
        self._prune(bucket, now)
        used = len(bucket.timestamps)
        allowed = used < self._config.max_alerts
        return BudgetResult(
            allowed=allowed,
            key=key,
            used=used,
            limit=self._config.max_alerts,
            window_seconds=self._config.window_seconds,
        )

    def consume(self, metric_key: str, now: Optional[datetime] = None) -> BudgetResult:
        """Check budget and, if allowed, record the alert."""
        now = now or datetime.utcnow()
        result = self.check(metric_key, now=now)
        if result.allowed:
            key = metric_key if self._config.per_key else "__global__"
            self._bucket_for(key).timestamps.append(now)
        return result

    def reset(self, metric_key: Optional[str] = None) -> None:
        """Clear recorded alerts for a key (or all keys)."""
        if metric_key is None:
            self._buckets.clear()
        else:
            key = metric_key if self._config.per_key else "__global__"
            self._buckets.pop(key, None)
