"""Drift detection: flag metrics whose baseline mean has shifted significantly."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class DriftConfig:
    """Configuration for drift detection."""
    min_samples: int = 10
    warn_threshold: float = 0.10   # 10 % relative shift
    critical_threshold: float = 0.25  # 25 % relative shift

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if self.warn_threshold <= 0:
            raise ValueError("warn_threshold must be positive")
        if self.critical_threshold <= self.warn_threshold:
            raise ValueError(
                "critical_threshold must be greater than warn_threshold"
            )

    @staticmethod
    def from_dict(data: dict) -> "DriftConfig":
        return DriftConfig(
            min_samples=data.get("min_samples", 10),
            warn_threshold=data.get("warn_threshold", 0.10),
            critical_threshold=data.get("critical_threshold", 0.25),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "warn_threshold": self.warn_threshold,
            "critical_threshold": self.critical_threshold,
        }


@dataclass
class DriftResult:
    """Result of a drift check for a single metric key."""
    metric_key: str
    baseline_mean: float
    current_mean: float
    relative_shift: float   # signed fractional change
    status: MetricStatus

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "baseline_mean": round(self.baseline_mean, 6),
            "current_mean": round(self.current_mean, 6),
            "relative_shift": round(self.relative_shift, 6),
            "status": self.status.value,
        }


@dataclass
class DriftDetector:
    """Detect mean drift between an early baseline window and a recent window."""
    config: DriftConfig = field(default_factory=DriftConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[DriftResult]:
        snapshots = history.all(key)
        n = len(snapshots)
        if n < self.config.min_samples:
            return None

        half = n // 2
        baseline_vals = [s.value for s in snapshots[:half]]
        current_vals = [s.value for s in snapshots[half:]]

        baseline_mean = sum(baseline_vals) / len(baseline_vals)
        current_mean = sum(current_vals) / len(current_vals)

        if baseline_mean == 0.0:
            relative_shift = 0.0
        else:
            relative_shift = (current_mean - baseline_mean) / abs(baseline_mean)

        abs_shift = abs(relative_shift)
        if abs_shift >= self.config.critical_threshold:
            status = MetricStatus.CRITICAL
        elif abs_shift >= self.config.warn_threshold:
            status = MetricStatus.WARNING
        else:
            status = MetricStatus.OK

        return DriftResult(
            metric_key=key,
            baseline_mean=baseline_mean,
            current_mean=current_mean,
            relative_shift=relative_shift,
            status=status,
        )

    def analyse_all(
        self, history: MetricHistory, keys: List[str]
    ) -> Dict[str, DriftResult]:
        results: Dict[str, DriftResult] = {}
        for key in keys:
            result = self.analyse(key, history)
            if result is not None:
                results[key] = result
        return results
