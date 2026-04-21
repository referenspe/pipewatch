"""Exponential decay weighting for metric history."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.history import MetricHistory


@dataclass
class DecayConfig:
    half_life: float = 60.0          # seconds; controls how fast older samples lose weight
    min_samples: int = 2

    def __post_init__(self) -> None:
        if self.half_life <= 0:
            raise ValueError("half_life must be positive")
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")

    @classmethod
    def from_dict(cls, data: dict) -> "DecayConfig":
        return cls(
            half_life=float(data.get("half_life", 60.0)),
            min_samples=int(data.get("min_samples", 2)),
        )

    def to_dict(self) -> dict:
        return {"half_life": self.half_life, "min_samples": self.min_samples}


@dataclass
class DecayResult:
    metric_key: str
    weighted_mean: float
    sample_count: int
    sufficient: bool

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "weighted_mean": self.weighted_mean,
            "sample_count": self.sample_count,
            "sufficient": self.sufficient,
        }


class DecayAnalyser:
    """Compute an exponentially-decayed weighted mean over recorded snapshots."""

    def __init__(self, config: Optional[DecayConfig] = None) -> None:
        self.config = config or DecayConfig()

    def analyse(self, key: str, history: MetricHistory) -> Optional[DecayResult]:
        snapshots = history.all(key)
        if not snapshots:
            return None

        sufficient = len(snapshots) >= self.config.min_samples
        if not sufficient:
            # Still compute but flag as insufficient
            pass

        # Sort oldest first
        sorted_snaps = sorted(snapshots, key=lambda s: s.recorded_at)
        latest_ts = sorted_snaps[-1].recorded_at

        decay_constant = math.log(2) / self.config.half_life

        total_weight = 0.0
        weighted_sum = 0.0
        for snap in sorted_snaps:
            age = latest_ts - snap.recorded_at
            weight = math.exp(-decay_constant * age)
            weighted_sum += snap.value * weight
            total_weight += weight

        weighted_mean = weighted_sum / total_weight if total_weight > 0 else 0.0

        return DecayResult(
            metric_key=key,
            weighted_mean=round(weighted_mean, 6),
            sample_count=len(snapshots),
            sufficient=sufficient,
        )

    def analyse_all(self, history: MetricHistory) -> List[DecayResult]:
        results = []
        for key in history.keys():
            result = self.analyse(key, history)
            if result is not None:
                results.append(result)
        return results
