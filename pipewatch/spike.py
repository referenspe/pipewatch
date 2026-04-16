"""Spike detection: flag sudden large jumps in metric values."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory


@dataclass
class SpikeConfig:
    min_samples: int = 5
    multiplier: float = 2.5  # value must exceed mean + multiplier * std_dev
    lookback: int = 20       # max snapshots considered

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")
        if self.lookback < self.min_samples:
            raise ValueError("lookback must be >= min_samples")

    @classmethod
    def from_dict(cls, data: dict) -> "SpikeConfig":
        return cls(
            min_samples=data.get("min_samples", 5),
            multiplier=float(data.get("multiplier", 2.5)),
            lookback=int(data.get("lookback", 20)),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "multiplier": self.multiplier,
            "lookback": self.lookback,
        }


@dataclass
class SpikeResult:
    metric_key: str
    current_value: float
    mean: float
    std_dev: float
    threshold: float
    is_spike: bool

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "current_value": self.current_value,
            "mean": round(self.mean, 4),
            "std_dev": round(self.std_dev, 4),
            "threshold": round(self.threshold, 4),
            "is_spike": self.is_spike,
        }


@dataclass
class SpikeDetector:
    config: SpikeConfig = field(default_factory=SpikeConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[SpikeResult]:
        snapshots = history.snapshots(key)
        if not snapshots:
            return None
        window = snapshots[-self.config.lookback :]
        if len(window) < self.config.min_samples:
            return None

        # Use all-but-last as baseline, last as current
        baseline = [s.value for s in window[:-1]]
        current = window[-1].value

        mean = sum(baseline) / len(baseline)
        variance = sum((v - mean) ** 2 for v in baseline) / len(baseline)
        std_dev = variance ** 0.5
        threshold = mean + self.config.multiplier * std_dev

        return SpikeResult(
            metric_key=key,
            current_value=current,
            mean=mean,
            std_dev=std_dev,
            threshold=threshold,
            is_spike=current > threshold,
        )

    def analyse_all(
        self, history: MetricHistory
    ) -> Dict[str, SpikeResult]:
        results: Dict[str, SpikeResult] = {}
        for key in history.keys():
            result = self.analyse(key, history)
            if result is not None:
                results[key] = result
        return results
