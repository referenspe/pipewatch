"""Outlier detection using IQR-based fencing for pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class OutlierConfig:
    min_samples: int = 8
    iqr_multiplier: float = 1.5
    severe_multiplier: float = 3.0

    def __post_init__(self) -> None:
        if self.min_samples < 4:
            raise ValueError("min_samples must be at least 4")
        if self.iqr_multiplier <= 0:
            raise ValueError("iqr_multiplier must be positive")
        if self.severe_multiplier <= self.iqr_multiplier:
            raise ValueError("severe_multiplier must be greater than iqr_multiplier")

    @classmethod
    def from_dict(cls, data: dict) -> "OutlierConfig":
        return cls(
            min_samples=data.get("min_samples", 8),
            iqr_multiplier=data.get("iqr_multiplier", 1.5),
            severe_multiplier=data.get("severe_multiplier", 3.0),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "iqr_multiplier": self.iqr_multiplier,
            "severe_multiplier": self.severe_multiplier,
        }


@dataclass
class OutlierResult:
    metric_key: str
    value: float
    q1: float
    q3: float
    iqr: float
    lower_fence: float
    upper_fence: float
    status: MetricStatus

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "value": self.value,
            "q1": self.q1,
            "q3": self.q3,
            "iqr": self.iqr,
            "lower_fence": self.lower_fence,
            "upper_fence": self.upper_fence,
            "status": self.status.value,
        }


def _percentile(sorted_values: List[float], pct: float) -> float:
    n = len(sorted_values)
    idx = pct / 100.0 * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_values[lo] + (idx - lo) * (sorted_values[hi] - sorted_values[lo])


@dataclass
class OutlierDetector:
    config: OutlierConfig = field(default_factory=OutlierConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[OutlierResult]:
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return None
        values = sorted(s.value for s in snapshots)
        latest = snapshots[-1].value
        q1 = _percentile(values, 25)
        q3 = _percentile(values, 75)
        iqr = q3 - q1
        lower = q1 - self.config.iqr_multiplier * iqr
        upper = q3 + self.config.iqr_multiplier * iqr
        severe_lower = q1 - self.config.severe_multiplier * iqr
        severe_upper = q3 + self.config.severe_multiplier * iqr
        if latest < severe_lower or latest > severe_upper:
            status = MetricStatus.CRITICAL
        elif latest < lower or latest > upper:
            status = MetricStatus.WARNING
        else:
            status = MetricStatus.OK
        return OutlierResult(
            metric_key=key,
            value=latest,
            q1=q1,
            q3=q3,
            iqr=iqr,
            lower_fence=lower,
            upper_fence=upper,
            status=status,
        )

    def analyse_all(
        self, keys: List[str], history: MetricHistory
    ) -> List[OutlierResult]:
        results = []
        for key in keys:
            result = self.analyse(key, history)
            if result is not None:
                results.append(result)
        return results
