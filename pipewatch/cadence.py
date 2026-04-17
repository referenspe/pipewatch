"""Cadence tracking — detect irregular metric collection intervals."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.history import MetricHistory


@dataclass
class CadenceConfig:
    expected_interval_seconds: float = 60.0
    tolerance_pct: float = 0.25  # 25% deviation allowed before warning
    critical_pct: float = 0.75  # 75% deviation triggers critical
    min_samples: int = 3

    def __post_init__(self) -> None:
        if self.expected_interval_seconds <= 0:
            raise ValueError("expected_interval_seconds must be positive")
        if not (0 < self.tolerance_pct < self.critical_pct <= 1.0):
            raise ValueError(
                "tolerance_pct must be < critical_pct and both in (0, 1]"
            )
        if self.min_samples < 2:
            raise ValueError("min_samples must be >= 2")

    @classmethod
    def from_dict(cls, data: dict) -> "CadenceConfig":
        return cls(
            expected_interval_seconds=data.get("expected_interval_seconds", 60.0),
            tolerance_pct=data.get("tolerance_pct", 0.25),
            critical_pct=data.get("critical_pct", 0.75),
            min_samples=data.get("min_samples", 3),
        )

    def to_dict(self) -> dict:
        return {
            "expected_interval_seconds": self.expected_interval_seconds,
            "tolerance_pct": self.tolerance_pct,
            "critical_pct": self.critical_pct,
            "min_samples": self.min_samples,
        }


@dataclass
class CadenceResult:
    metric_key: str
    mean_interval: float
    deviation_pct: float
    level: str  # "ok", "warning", "critical", "insufficient_data"
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "mean_interval": round(self.mean_interval, 3),
            "deviation_pct": round(self.deviation_pct, 4),
            "level": self.level,
            "sample_count": self.sample_count,
        }


@dataclass
class CadenceAnalyser:
    config: CadenceConfig = field(default_factory=CadenceConfig)

    def analyse(self, key: str, history: MetricHistory) -> CadenceResult:
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return CadenceResult(
                metric_key=key,
                mean_interval=0.0,
                deviation_pct=0.0,
                level="insufficient_data",
                sample_count=len(snapshots),
            )

        timestamps = [s.timestamp for s in snapshots]
        intervals = [
            (timestamps[i] - timestamps[i - 1]).total_seconds()
            for i in range(1, len(timestamps))
        ]
        mean_interval = sum(intervals) / len(intervals)
        deviation_pct = abs(
            mean_interval - self.config.expected_interval_seconds
        ) / self.config.expected_interval_seconds

        if deviation_pct >= self.config.critical_pct:
            level = "critical"
        elif deviation_pct >= self.config.tolerance_pct:
            level = "warning"
        else:
            level = "ok"

        return CadenceResult(
            metric_key=key,
            mean_interval=mean_interval,
            deviation_pct=deviation_pct,
            level=level,
            sample_count=len(snapshots),
        )
