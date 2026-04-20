"""Staleness detection for pipeline metrics.

Detects metrics that have not been updated within an expected interval,
classifying them as stale or critically stale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory


@dataclass
class StalenessConfig:
    stale_after: int = 60          # seconds before a metric is considered stale
    critical_after: int = 300      # seconds before a metric is considered critically stale

    def __post_init__(self) -> None:
        if self.stale_after <= 0:
            raise ValueError("stale_after must be positive")
        if self.critical_after <= self.stale_after:
            raise ValueError("critical_after must be greater than stale_after")

    @classmethod
    def from_dict(cls, data: dict) -> "StalenessConfig":
        return cls(
            stale_after=data.get("stale_after", 60),
            critical_after=data.get("critical_after", 300),
        )

    def to_dict(self) -> dict:
        return {
            "stale_after": self.stale_after,
            "critical_after": self.critical_after,
        }


@dataclass
class StalenessResult:
    metric_key: str
    last_seen: Optional[datetime]
    age_seconds: Optional[float]   # None when no data has ever been recorded
    is_stale: bool
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "age_seconds": self.age_seconds,
            "is_stale": self.is_stale,
            "is_critical": self.is_critical,
        }


@dataclass
class StalenessDetector:
    config: StalenessConfig = field(default_factory=StalenessConfig)

    def check(self, key: str, history: MetricHistory,
              now: Optional[datetime] = None) -> StalenessResult:
        """Return a StalenessResult for the given metric history."""
        if now is None:
            now = datetime.now(timezone.utc)

        latest = history.latest(key)
        if latest is None:
            return StalenessResult(
                metric_key=key,
                last_seen=None,
                age_seconds=None,
                is_stale=True,
                is_critical=True,
            )

        ts = latest.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        age = (now - ts).total_seconds()
        return StalenessResult(
            metric_key=key,
            last_seen=ts,
            age_seconds=age,
            is_stale=age >= self.config.stale_after,
            is_critical=age >= self.config.critical_after,
        )

    def check_all(self, histories: Dict[str, MetricHistory],
                  now: Optional[datetime] = None) -> List[StalenessResult]:
        """Check staleness for every key in the supplied histories mapping."""
        return [self.check(key, hist, now) for key, hist in histories.items()]
