"""Sliding window aggregation over metric history."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class WindowConfig:
    size: int = 10
    min_samples: int = 2

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError("size must be at least 1")
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if self.min_samples > self.size:
            raise ValueError("min_samples cannot exceed size")

    @classmethod
    def from_dict(cls, data: Dict) -> "WindowConfig":
        return cls(
            size=data.get("size", 10),
            min_samples=data.get("min_samples", 2),
        )

    def to_dict(self) -> Dict:
        return {"size": self.size, "min_samples": self.min_samples}


@dataclass
class WindowResult:
    key: str
    values: List[float]
    mean: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]
    sufficient: bool

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "mean": self.mean,
            "min": self.minimum,
            "max": self.maximum,
            "sample_count": len(self.values),
            "sufficient": self.sufficient,
        }


class WindowAggregator:
    def __init__(self, config: Optional[WindowConfig] = None) -> None:
        self._config = config or WindowConfig()

    def compute(self, key: str, history: "MetricHistory") -> WindowResult:  # type: ignore[name-defined]
        from pipewatch.history import MetricHistory  # noqa: F401

        snapshots = history.recent(self._config.size)
        values = [s.value for s in snapshots]
        sufficient = len(values) >= self._config.min_samples

        if sufficient:
            mean = sum(values) / len(values)
            minimum = min(values)
            maximum = max(values)
        else:
            mean = minimum = maximum = None

        return WindowResult(
            key=key,
            values=values,
            mean=mean,
            minimum=minimum,
            maximum=maximum,
            sufficient=sufficient,
        )
