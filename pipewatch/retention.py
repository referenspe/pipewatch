"""Retention policy for pruning old metric history entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from pipewatch.history import MetricHistory, MetricSnapshot


@dataclass
class RetentionPolicy:
    """Configuration for how long metric snapshots are kept."""

    max_age_seconds: float = 3600.0  # 1 hour default
    max_entries: int = 1000

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")

    @classmethod
    def from_dict(cls, data: dict) -> "RetentionPolicy":
        return cls(
            max_age_seconds=float(data.get("max_age_seconds", 3600.0)),
            max_entries=int(data.get("max_entries", 1000)),
        )

    def to_dict(self) -> dict:
        return {
            "max_age_seconds": self.max_age_seconds,
            "max_entries": self.max_entries,
        }


@dataclass
class RetentionResult:
    """Summary of a retention pruning operation."""

    metric_key: str
    removed_count: int
    remaining_count: int

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "removed_count": self.removed_count,
            "remaining_count": self.remaining_count,
        }


class RetentionManager:
    """Applies a RetentionPolicy to one or more MetricHistory stores."""

    def __init__(self, policy: RetentionPolicy) -> None:
        self._policy = policy

    def prune(self, key: str, history: MetricHistory) -> RetentionResult:
        """Remove snapshots that violate the policy from *history*."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(
            seconds=self._policy.max_age_seconds
        )

        snapshots: List[MetricSnapshot] = list(history.all(key))
        before = len(snapshots)

        # Filter by age first
        snapshots = [s for s in snapshots if s.recorded_at >= cutoff]

        # Then enforce max_entries (keep the most recent)
        if len(snapshots) > self._policy.max_entries:
            snapshots = snapshots[-self._policy.max_entries :]

        removed = before - len(snapshots)
        history.replace(key, snapshots)

        return RetentionResult(
            metric_key=key,
            removed_count=removed,
            remaining_count=len(snapshots),
        )

    def prune_all(
        self, histories: Dict[str, MetricHistory]
    ) -> List[RetentionResult]:
        """Prune every history store and return one result per key."""
        results = []
        for key, history in histories.items():
            results.append(self.prune(key, history))
        return results
