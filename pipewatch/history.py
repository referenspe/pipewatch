"""In-memory metric history tracking for trend detection."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List, Optional

from pipewatch.metrics import MetricStatus, PipelineMetric


@dataclass
class MetricSnapshot:
    """A single recorded observation of a metric."""

    metric: PipelineMetric
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def value(self) -> float:
        return self.metric.value

    @property
    def status(self) -> MetricStatus:
        return self.metric.status


@dataclass
class MetricHistory:
    """Bounded history of snapshots for a single metric key."""

    metric_key: str
    max_entries: int = 100
    _snapshots: Deque[MetricSnapshot] = field(default_factory=deque, init=False, repr=False)

    def record(self, metric: PipelineMetric) -> None:
        """Append a new snapshot, evicting oldest when capacity is exceeded."""
        self._snapshots.append(MetricSnapshot(metric=metric))
        if len(self._snapshots) > self.max_entries:
            self._snapshots.popleft()

    def snapshots(self) -> List[MetricSnapshot]:
        """Return snapshots in chronological order."""
        return list(self._snapshots)

    def latest(self) -> Optional[MetricSnapshot]:
        """Return the most recent snapshot, or None if empty."""
        return self._snapshots[-1] if self._snapshots else None

    def values(self) -> List[float]:
        return [s.value for s in self._snapshots]

    def average(self) -> Optional[float]:
        vals = self.values()
        return sum(vals) / len(vals) if vals else None

    def consecutive_status_count(self, status: MetricStatus) -> int:
        """Count how many trailing snapshots share *status* consecutively."""
        count = 0
        for snap in reversed(self._snapshots):
            if snap.status == status:
                count += 1
            else:
                break
        return count


class HistoryStore:
    """Registry of MetricHistory objects keyed by metric_key."""

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._histories: Dict[str, MetricHistory] = {}

    def record(self, metric: PipelineMetric) -> None:
        key = metric.key
        if key not in self._histories:
            self._histories[key] = MetricHistory(
                metric_key=key, max_entries=self._max_entries
            )
        self._histories[key].record(metric)

    def get(self, metric_key: str) -> Optional[MetricHistory]:
        return self._histories.get(metric_key)

    def all_keys(self) -> List[str]:
        return list(self._histories.keys())
