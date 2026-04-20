"""Throughput monitoring for pipeline stages.

Tracks the rate at which metrics are processed over a sliding window
and raises warnings or critical alerts when throughput drops below
configured thresholds.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class ThroughputConfig:
    """Configuration for throughput monitoring."""

    # Minimum acceptable events per second (warning threshold)
    warn_below: float = 1.0
    # Events per second below which status is CRITICAL
    critical_below: float = 0.1
    # Sliding window size (number of snapshots to consider)
    window_size: int = 10
    # Minimum snapshots required before evaluation is meaningful
    min_samples: int = 2

    def __post_init__(self) -> None:
        if self.warn_below <= 0:
            raise ValueError("warn_below must be positive")
        if self.critical_below <= 0:
            raise ValueError("critical_below must be positive")
        if self.critical_below >= self.warn_below:
            raise ValueError("critical_below must be less than warn_below")
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")

    @classmethod
    def from_dict(cls, data: Dict) -> "ThroughputConfig":
        return cls(
            warn_below=data.get("warn_below", 1.0),
            critical_below=data.get("critical_below", 0.1),
            window_size=data.get("window_size", 10),
            min_samples=data.get("min_samples", 2),
        )

    def to_dict(self) -> Dict:
        return {
            "warn_below": self.warn_below,
            "critical_below": self.critical_below,
            "window_size": self.window_size,
            "min_samples": self.min_samples,
        }


@dataclass
class ThroughputResult:
    """Result of a throughput evaluation for a single metric key."""

    metric_key: str
    events_per_second: float
    status: MetricStatus
    sample_count: int
    mean_interval_seconds: float

    def to_dict(self) -> Dict:
        return {
            "metric_key": self.metric_key,
            "events_per_second": round(self.events_per_second, 4),
            "status": self.status.value,
            "sample_count": self.sample_count,
            "mean_interval_seconds": round(self.mean_interval_seconds, 4),
        }


@dataclass
class ThroughputMonitor:
    """Evaluates throughput for tracked metric histories."""

    config: ThroughputConfig = field(default_factory=ThroughputConfig)

    def evaluate(self, key: str, history: MetricHistory) -> Optional[ThroughputResult]:
        """Evaluate throughput for a single metric key.

        Returns None if there are insufficient samples to compute a rate.
        """
        snapshots = history.snapshots(key)
        window = snapshots[-self.config.window_size :] if snapshots else []

        if len(window) < self.config.min_samples:
            return None

        timestamps = [s.timestamp for s in window]
        intervals = [
            (timestamps[i] - timestamps[i - 1]).total_seconds()
            for i in range(1, len(timestamps))
            if (timestamps[i] - timestamps[i - 1]).total_seconds() > 0
        ]

        if not intervals:
            return None

        mean_interval = statistics.mean(intervals)
        events_per_second = 1.0 / mean_interval if mean_interval > 0 else 0.0

        if events_per_second < self.config.critical_below:
            status = MetricStatus.CRITICAL
        elif events_per_second < self.config.warn_below:
            status = MetricStatus.WARNING
        else:
            status = MetricStatus.OK

        return ThroughputResult(
            metric_key=key,
            events_per_second=events_per_second,
            status=status,
            sample_count=len(window),
            mean_interval_seconds=mean_interval,
        )

    def evaluate_all(
        self, history: MetricHistory, keys: List[str]
    ) -> Dict[str, ThroughputResult]:
        """Evaluate throughput for multiple metric keys.

        Keys with insufficient data are omitted from the result.
        """
        results: Dict[str, ThroughputResult] = {}
        for key in keys:
            result = self.evaluate(key, history)
            if result is not None:
                results[key] = result
        return results
