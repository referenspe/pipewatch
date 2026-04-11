"""Simple linear-extrapolation forecaster for pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from pipewatch.history import MetricHistory


class ForecastConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ForecastResult:
    metric_key: str
    predicted_value: float
    steps_ahead: int
    confidence: ForecastConfidence
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "predicted_value": round(self.predicted_value, 4),
            "steps_ahead": self.steps_ahead,
            "confidence": self.confidence.value,
            "sample_count": self.sample_count,
        }


def _linear_forecast(values: List[float], steps_ahead: int) -> float:
    """Least-squares linear extrapolation."""
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator if denominator != 0 else 0.0
    intercept = mean_y - slope * mean_x
    return intercept + slope * (n - 1 + steps_ahead)


def _confidence(sample_count: int) -> ForecastConfidence:
    if sample_count >= 20:
        return ForecastConfidence.HIGH
    if sample_count >= 10:
        return ForecastConfidence.MEDIUM
    return ForecastConfidence.LOW


@dataclass
class Forecaster:
    min_samples: int = 3
    steps_ahead: int = 1

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if self.steps_ahead < 1:
            raise ValueError("steps_ahead must be at least 1")

    def forecast(self, key: str, history: MetricHistory) -> Optional[ForecastResult]:
        snapshots = history.all(key)
        if len(snapshots) < self.min_samples:
            return None
        values = [s.value for s in snapshots]
        predicted = _linear_forecast(values, self.steps_ahead)
        return ForecastResult(
            metric_key=key,
            predicted_value=predicted,
            steps_ahead=self.steps_ahead,
            confidence=_confidence(len(values)),
            sample_count=len(values),
        )

    def forecast_all(self, history: MetricHistory) -> List[ForecastResult]:
        results = []
        for key in history.keys():
            result = self.forecast(key, history)
            if result is not None:
                results.append(result)
        return results
