"""Tracks historical snapshots of pipeline metric values."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pipewatch.metrics import PipelineMetric, MetricStatus


@dataclass
class MetricSnapshot:
    """A point-in-time reading of a single pipeline metric."""

    metric_key: str
    timestamp: datetime
    value: float
    status: MetricStatus

    @classmethod
    def from_metric(cls, metric: PipelineMetric) -> "MetricSnapshot":
        return cls(
            metric_key=metric.key,
            timestamp=datetime.now(tz=timezone.utc),
            value=metric.value,
            status=metric.status,
        )


class MetricHistory:
    """Stores rolling snapshots for multiple metric keys."""

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._store: Dict[str, List[MetricSnapshot]] = {}

    def record(self, metric: PipelineMetric) -> None:
        """Record a new snapshot for the given metric."""
        snapshot = MetricSnapshot.from_metric(metric)
        bucket = self._store.setdefault(metric.key, [])
        bucket.append(snapshot)
        if len(bucket) > self._max_entries:
            bucket.pop(0)

    def latest(self, metric_key: str) -> Optional[MetricSnapshot]:
        """Return the most recent snapshot for a key, or None."""
        bucket = self._store.get(metric_key, [])
        return bucket[-1] if bucket else None

    def all(self, metric_key: str) -> List[MetricSnapshot]:
        """Return all snapshots for a key in chronological order."""
        return list(self._store.get(metric_key, []))

    def keys(self) -> List[str]:
        """Return all tracked metric keys."""
        return list(self._store.keys())

    def clear(self, metric_key: Optional[str] = None) -> None:
        """Clear history for a specific key or all keys."""
        if metric_key is not None:
            self._store.pop(metric_key, None)
        else:
            self._store.clear()

    def count(self, metric_key: str) -> int:
        """Return the number of stored snapshots for a key."""
        return len(self._store.get(metric_key, []))
