"""Thin time-series store for pipeline metric snapshots."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from pipewatch.metrics import PipelineMetric


@dataclass
class MetricSnapshot:
    """A single recorded observation of a metric."""

    key: str
    value: float
    status: str
    recorded_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    @classmethod
    def from_metric(cls, metric: PipelineMetric) -> "MetricSnapshot":
        return cls(
            key=metric.key,
            value=metric.value,
            status=metric.status.value,
        )


class MetricHistory:
    """In-memory ring-store for MetricSnapshot objects."""

    def __init__(self) -> None:
        self._store: Dict[str, List[MetricSnapshot]] = defaultdict(list)

    def record(self, metric: PipelineMetric) -> None:
        snapshot = MetricSnapshot.from_metric(metric)
        self._store[metric.key].append(snapshot)

    def latest(self, key: str) -> Optional[MetricSnapshot]:
        entries = self._store.get(key, [])
        return entries[-1] if entries else None

    def all(self, key: str) -> Iterable[MetricSnapshot]:
        return list(self._store.get(key, []))

    def replace(self, key: str, snapshots: List[MetricSnapshot]) -> None:
        """Overwrite stored snapshots for *key* (used by retention pruning)."""
        self._store[key] = list(snapshots)

    def keys(self) -> Iterable[str]:
        return list(self._store.keys())

    def clear(self, key: str) -> None:
        self._store.pop(key, None)
