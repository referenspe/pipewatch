"""Trend analysis for pipeline metrics based on historical snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from pipewatch.history import MetricHistory, MetricSnapshot


class TrendDirection(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class TrendResult:
    key: str
    direction: TrendDirection
    slope: Optional[float]  # average change per interval
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "direction": self.direction.value,
            "slope": self.slope,
            "sample_count": self.sample_count,
        }


class TrendAnalyser:
    """Analyses metric history to determine value trends."""

    def __init__(self, min_samples: int = 3, stable_threshold: float = 0.05) -> None:
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        self.min_samples = min_samples
        self.stable_threshold = stable_threshold

    def analyse(self, key: str, history: MetricHistory) -> TrendResult:
        """Return a TrendResult for the given metric key."""
        snapshots: List[MetricSnapshot] = history.all(key)
        if len(snapshots) < self.min_samples:
            return TrendResult(
                key=key,
                direction=TrendDirection.UNKNOWN,
                slope=None,
                sample_count=len(snapshots),
            )

        values = [s.value for s in snapshots]
        deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
        slope = sum(deltas) / len(deltas)

        if abs(slope) <= self.stable_threshold:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.RISING
        else:
            direction = TrendDirection.FALLING

        return TrendResult(
            key=key,
            direction=direction,
            slope=round(slope, 6),
            sample_count=len(snapshots),
        )

    def analyse_all(self, history: MetricHistory) -> List[TrendResult]:
        """Analyse every key tracked in the given history."""
        return [self.analyse(key, history) for key in history.keys()]
