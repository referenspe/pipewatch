"""Anomaly detection for pipeline metrics using z-score analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from pipewatch.history import MetricHistory


class AnomalyLevel(str, Enum):
    NONE = "none"
    MILD = "mild"
    SEVERE = "severe"


@dataclass
class AnomalyResult:
    metric_key: str
    value: float
    mean: float
    std_dev: float
    z_score: float
    level: AnomalyLevel

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "value": self.value,
            "mean": round(self.mean, 4),
            "std_dev": round(self.std_dev, 4),
            "z_score": round(self.z_score, 4),
            "level": self.level.value,
        }


@dataclass
class AnomalyDetector:
    mild_threshold: float = 2.0
    severe_threshold: float = 3.5
    min_samples: int = 5

    def __post_init__(self) -> None:
        if self.mild_threshold <= 0:
            raise ValueError("mild_threshold must be positive")
        if self.severe_threshold <= self.mild_threshold:
            raise ValueError("severe_threshold must exceed mild_threshold")
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")

    def detect(self, history: MetricHistory, metric_key: str) -> Optional[AnomalyResult]:
        snapshots = history.all(metric_key)
        if len(snapshots) < self.min_samples:
            return None

        values: List[float] = [s.value for s in snapshots]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        latest = values[-1]
        z_score = (latest - mean) / std_dev if std_dev > 0 else 0.0
        abs_z = abs(z_score)

        if abs_z >= self.severe_threshold:
            level = AnomalyLevel.SEVERE
        elif abs_z >= self.mild_threshold:
            level = AnomalyLevel.MILD
        else:
            level = AnomalyLevel.NONE

        return AnomalyResult(
            metric_key=metric_key,
            value=latest,
            mean=mean,
            std_dev=std_dev,
            z_score=z_score,
            level=level,
        )

    def detect_all(self, history: MetricHistory) -> List[AnomalyResult]:
        results = []
        for key in history.keys():
            result = self.detect(history, key)
            if result is not None:
                results.append(result)
        return results
