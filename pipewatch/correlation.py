"""Correlation analysis between pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pipewatch.history import MetricHistory


class CorrelationStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass
class CorrelationResult:
    key_a: str
    key_b: str
    coefficient: float  # Pearson r, range [-1, 1]
    strength: CorrelationStrength
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "key_a": self.key_a,
            "key_b": self.key_b,
            "coefficient": round(self.coefficient, 4),
            "strength": self.strength.value,
            "sample_count": self.sample_count,
        }


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def _classify(r: float) -> CorrelationStrength:
    abs_r = abs(r)
    if abs_r >= 0.7:
        return CorrelationStrength.STRONG
    if abs_r >= 0.4:
        return CorrelationStrength.MODERATE
    if abs_r >= 0.1:
        return CorrelationStrength.WEAK
    return CorrelationStrength.NONE


@dataclass
class CorrelationAnalyser:
    min_samples: int = 5

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")

    def analyse(
        self,
        history_a: MetricHistory,
        history_b: MetricHistory,
    ) -> Optional[CorrelationResult]:
        vals_a = [s.value for s in history_a.snapshots]
        vals_b = [s.value for s in history_b.snapshots]
        n = min(len(vals_a), len(vals_b))
        if n < self.min_samples:
            return None
        xs = vals_a[-n:]
        ys = vals_b[-n:]
        r = _pearson(xs, ys)
        return CorrelationResult(
            key_a=history_a.metric_key,
            key_b=history_b.metric_key,
            coefficient=r,
            strength=_classify(r),
            sample_count=n,
        )

    def analyse_all(
        self,
        histories: Dict[str, MetricHistory],
    ) -> List[CorrelationResult]:
        keys = list(histories.keys())
        results: List[CorrelationResult] = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                result = self.analyse(histories[keys[i]], histories[keys[j]])
                if result is not None:
                    results.append(result)
        return results
