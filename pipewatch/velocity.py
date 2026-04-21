"""Velocity tracking for pipeline metrics.

Measures the rate of change (first derivative) of a metric over time,
detecting acceleration or deceleration in pipeline data flows.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class VelocityConfig:
    """Configuration for velocity analysis."""

    min_samples: int = 3
    warn_rate: float = 10.0   # units per second
    critical_rate: float = 25.0  # units per second
    direction: str = "either"  # "rising", "falling", or "either"

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if self.warn_rate <= 0:
            raise ValueError("warn_rate must be positive")
        if self.critical_rate <= self.warn_rate:
            raise ValueError("critical_rate must be greater than warn_rate")
        if self.direction not in ("rising", "falling", "either"):
            raise ValueError("direction must be 'rising', 'falling', or 'either'")

    @classmethod
    def from_dict(cls, data: dict) -> "VelocityConfig":
        return cls(
            min_samples=data.get("min_samples", 3),
            warn_rate=data.get("warn_rate", 10.0),
            critical_rate=data.get("critical_rate", 25.0),
            direction=data.get("direction", "either"),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "warn_rate": self.warn_rate,
            "critical_rate": self.critical_rate,
            "direction": self.direction,
        }


@dataclass
class VelocityResult:
    """Result of a velocity analysis for a single metric key."""

    metric_key: str
    rate_per_second: float
    status: MetricStatus
    sample_count: int
    message: str

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "rate_per_second": self.rate_per_second,
            "status": self.status.value,
            "sample_count": self.sample_count,
            "message": self.message,
        }


def _compute_rate(timestamps: List[float], values: List[float]) -> float:
    """Estimate the average rate of change (units/second) using finite differences."""
    if len(timestamps) < 2:
        return 0.0
    rates: List[float] = []
    for i in range(1, len(timestamps)):
        dt = timestamps[i] - timestamps[i - 1]
        if dt <= 0:
            continue
        dv = values[i] - values[i - 1]
        rates.append(dv / dt)
    return statistics.mean(rates) if rates else 0.0


@dataclass
class VelocityAnalyser:
    """Analyses the rate of change for metrics stored in a MetricHistory."""

    config: VelocityConfig = field(default_factory=VelocityConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[VelocityResult]:
        """Return a VelocityResult for *key*, or None if insufficient data."""
        snapshots = history.snapshots(key)
        if len(snapshots) < self.config.min_samples:
            return None

        timestamps = [s.timestamp for s in snapshots]
        values = [s.value for s in snapshots]

        rate = _compute_rate(timestamps, values)
        abs_rate = abs(rate)

        # Determine whether the direction is relevant
        direction_match = (
            self.config.direction == "either"
            or (self.config.direction == "rising" and rate > 0)
            or (self.config.direction == "falling" and rate < 0)
        )

        effective_rate = abs_rate if direction_match else 0.0

        if effective_rate >= self.config.critical_rate:
            status = MetricStatus.CRITICAL
            message = f"rate {rate:+.3f}/s exceeds critical threshold {self.config.critical_rate}/s"
        elif effective_rate >= self.config.warn_rate:
            status = MetricStatus.WARNING
            message = f"rate {rate:+.3f}/s exceeds warning threshold {self.config.warn_rate}/s"
        else:
            status = MetricStatus.OK
            message = f"rate {rate:+.3f}/s within acceptable bounds"

        return VelocityResult(
            metric_key=key,
            rate_per_second=rate,
            status=status,
            sample_count=len(snapshots),
            message=message,
        )

    def analyse_all(
        self, history: MetricHistory
    ) -> List[VelocityResult]:
        """Analyse velocity for every key present in *history*."""
        results: List[VelocityResult] = []
        for key in history.keys():
            result = self.analyse(key, history)
            if result is not None:
                results.append(result)
        return results
