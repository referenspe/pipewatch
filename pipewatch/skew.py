"""Skew detection: measures asymmetry in metric value distributions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory


@dataclass
class SkewConfig:
    min_samples: int = 10
    mild_threshold: float = 1.0
    severe_threshold: float = 2.0

    def __post_init__(self) -> None:
        if self.min_samples < 3:
            raise ValueError("min_samples must be at least 3")
        if self.mild_threshold <= 0:
            raise ValueError("mild_threshold must be positive")
        if self.severe_threshold <= self.mild_threshold:
            raise ValueError("severe_threshold must be greater than mild_threshold")

    @classmethod
    def from_dict(cls, data: dict) -> "SkewConfig":
        return cls(
            min_samples=data.get("min_samples", 10),
            mild_threshold=data.get("mild_threshold", 1.0),
            severe_threshold=data.get("severe_threshold", 2.0),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "mild_threshold": self.mild_threshold,
            "severe_threshold": self.severe_threshold,
        }


@dataclass
class SkewResult:
    metric_key: str
    sample_count: int
    skewness: float
    is_severe: bool
    is_mild: bool

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "sample_count": self.sample_count,
            "skewness": round(self.skewness, 4),
            "is_severe": self.is_severe,
            "is_mild": self.is_mild,
        }


def _skewness(values: List[float]) -> float:
    """Compute Pearson's moment coefficient of skewness."""
    n = len(values)
    if n < 3:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    if variance == 0.0:
        return 0.0
    std = variance ** 0.5
    return sum(((v - mean) / std) ** 3 for v in values) / n


@dataclass
class SkewDetector:
    config: SkewConfig = field(default_factory=SkewConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[SkewResult]:
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return None
        values = [s.value for s in snapshots]
        skew = _skewness(values)
        abs_skew = abs(skew)
        return SkewResult(
            metric_key=key,
            sample_count=len(values),
            skewness=skew,
            is_severe=abs_skew >= self.config.severe_threshold,
            is_mild=self.config.mild_threshold <= abs_skew < self.config.severe_threshold,
        )

    def analyse_all(
        self, history: MetricHistory, keys: List[str]
    ) -> Dict[str, SkewResult]:
        results: Dict[str, SkewResult] = {}
        for key in keys:
            result = self.analyse(key, history)
            if result is not None:
                results[key] = result
        return results
