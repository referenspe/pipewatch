"""Saturation detection for pipeline metrics.

Detects when a metric is approaching or exceeding a defined capacity
limit, useful for identifying resource exhaustion before it becomes
critical (e.g. queue fill-level, thread pool usage, memory headroom).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.metrics import MetricStatus, PipelineMetric
from pipewatch.history import MetricHistory


@dataclass
class SaturationConfig:
    """Configuration for saturation detection.

    Attributes:
        capacity:      The maximum expected value (100 % full).
        warn_pct:      Percentage of capacity that triggers a WARNING  (0–100).
        critical_pct:  Percentage of capacity that triggers a CRITICAL (0–100).
        min_samples:   Minimum history entries required before evaluating.
    """

    capacity: float
    warn_pct: float = 75.0
    critical_pct: float = 90.0
    min_samples: int = 1

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if not (0 < self.warn_pct < 100):
            raise ValueError("warn_pct must be between 0 and 100 (exclusive)")
        if not (0 < self.critical_pct <= 100):
            raise ValueError("critical_pct must be between 0 and 100 (inclusive)")
        if self.critical_pct <= self.warn_pct:
            raise ValueError("critical_pct must be greater than warn_pct")
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")

    @staticmethod
    def from_dict(data: Dict) -> "SaturationConfig":
        return SaturationConfig(
            capacity=float(data["capacity"]),
            warn_pct=float(data.get("warn_pct", 75.0)),
            critical_pct=float(data.get("critical_pct", 90.0)),
            min_samples=int(data.get("min_samples", 1)),
        )

    def to_dict(self) -> Dict:
        return {
            "capacity": self.capacity,
            "warn_pct": self.warn_pct,
            "critical_pct": self.critical_pct,
            "min_samples": self.min_samples,
        }


@dataclass
class SaturationResult:
    """Result of a saturation check for a single metric key."""

    metric_key: str
    current_value: float
    capacity: float
    fill_pct: float          # 0–100
    status: MetricStatus
    message: str

    def to_dict(self) -> Dict:
        return {
            "metric_key": self.metric_key,
            "current_value": self.current_value,
            "capacity": self.capacity,
            "fill_pct": round(self.fill_pct, 2),
            "status": self.status.value,
            "message": self.message,
        }


@dataclass
class SaturationDetector:
    """Evaluates metric values against a capacity ceiling."""

    config: SaturationConfig
    _results: List[SaturationResult] = field(default_factory=list, init=False)

    def analyse(
        self,
        key: str,
        history: MetricHistory,
        metric: Optional[PipelineMetric] = None,
    ) -> Optional[SaturationResult]:
        """Evaluate the latest value for *key* and return a SaturationResult.

        Returns ``None`` when there are insufficient samples.
        """
        snapshots = history.snapshots_for(key)
        if len(snapshots) < self.config.min_samples:
            return None

        # Use the provided metric or fall back to the most recent snapshot value.
        current = metric.value if metric is not None else snapshots[-1].value
        fill_pct = (current / self.config.capacity) * 100.0

        if fill_pct >= self.config.critical_pct:
            status = MetricStatus.CRITICAL
            message = (
                f"{key} is at {fill_pct:.1f}% of capacity "
                f"(>= critical threshold {self.config.critical_pct}%)"
            )
        elif fill_pct >= self.config.warn_pct:
            status = MetricStatus.WARNING
            message = (
                f"{key} is at {fill_pct:.1f}% of capacity "
                f"(>= warning threshold {self.config.warn_pct}%)"
            )
        else:
            status = MetricStatus.OK
            message = f"{key} is at {fill_pct:.1f}% of capacity (within limits)"

        result = SaturationResult(
            metric_key=key,
            current_value=current,
            capacity=self.config.capacity,
            fill_pct=fill_pct,
            status=status,
            message=message,
        )
        self._results.append(result)
        return result

    def analyse_all(
        self,
        history: MetricHistory,
        metrics: Optional[Dict[str, PipelineMetric]] = None,
    ) -> List[SaturationResult]:
        """Run saturation analysis across all tracked keys in *history*."""
        results: List[SaturationResult] = []
        for key in history.keys():
            metric = (metrics or {}).get(key)
            result = self.analyse(key, history, metric=metric)
            if result is not None:
                results.append(result)
        return results
