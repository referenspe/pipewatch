"""Surge detection: identify sudden large increases in metric values."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class SurgeConfig:
    min_samples: int = 3
    warn_multiplier: float = 2.0
    critical_multiplier: float = 4.0

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if self.warn_multiplier <= 1.0:
            raise ValueError("warn_multiplier must be greater than 1.0")
        if self.critical_multiplier <= self.warn_multiplier:
            raise ValueError("critical_multiplier must be greater than warn_multiplier")

    @classmethod
    def from_dict(cls, data: dict) -> "SurgeConfig":
        return cls(
            min_samples=data.get("min_samples", 3),
            warn_multiplier=data.get("warn_multiplier", 2.0),
            critical_multiplier=data.get("critical_multiplier", 4.0),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "warn_multiplier": self.warn_multiplier,
            "critical_multiplier": self.critical_multiplier,
        }


@dataclass
class SurgeResult:
    metric_key: str
    status: MetricStatus
    latest_value: float
    baseline_mean: float
    multiplier: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "status": self.status.value,
            "latest_value": self.latest_value,
            "baseline_mean": self.baseline_mean,
            "multiplier": round(self.multiplier, 4),
            "sample_count": self.sample_count,
        }


@dataclass
class SurgeDetector:
    config: SurgeConfig = field(default_factory=SurgeConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[SurgeResult]:
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return None

        baseline_snapshots = snapshots[:-1]
        baseline_mean = sum(s.value for s in baseline_snapshots) / len(baseline_snapshots)
        if baseline_mean == 0.0:
            return None

        latest = snapshots[-1].value
        multiplier = latest / baseline_mean

        if multiplier >= self.config.critical_multiplier:
            status = MetricStatus.CRITICAL
        elif multiplier >= self.config.warn_multiplier:
            status = MetricStatus.WARNING
        else:
            status = MetricStatus.OK

        return SurgeResult(
            metric_key=key,
            status=status,
            latest_value=latest,
            baseline_mean=baseline_mean,
            multiplier=multiplier,
            sample_count=len(snapshots),
        )
