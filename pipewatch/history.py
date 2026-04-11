"""In-memory metric history store with snapshot recording."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from pipewatch.metrics import MetricStatus, PipelineMetric


@dataclass
class MetricSnapshot:
    key: str
    value: float
    status: MetricStatus
    timestamp: float

    @classmethod
    def from_metric(cls, metric: PipelineMetric, timestamp: float) -> "MetricSnapshot":
        return cls(
            key=metric.key,
            value=metric.value,
            status=metric.status,
            timestamp=timestamp,
        )


class MetricHistory:
    """Stores ordered snapshots per metric key."""

    def __init__(self, max_per_key: int = 100) -> None:
        self.max_per_key = max_per_key
        self._store: Dict[str, List[MetricSnapshot]] = {}

    def record(self, snapshot: MetricSnapshot) -> None:
        bucket = self._store.setdefault(snapshot.key, [])
        bucket.append(snapshot)
        if len(bucket) > self.max_per_key:
            bucket.pop(0)

    def latest(self, key: str) -> Optional[MetricSnapshot]:
        bucket = self._store.get(key, [])
        return bucket[-1] if bucket else None

    def all(self, key: str) -> List[MetricSnapshot]:
        return list(self._store.get(key, []))

    def keys(self) -> List[str]:
        return list(self._store.keys())

    def clear(self, key: str) -> None:
        self._store.pop(key, None)

    def clear_all(self) -> None:
        self._store.clear()

    def count(self, key: str) -> int:
        return len(self._store.get(key, []))
