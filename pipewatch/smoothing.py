"""Exponential moving average smoothing for pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SmoothingConfig:
    alpha: float = 0.3  # EMA smoothing factor, 0 < alpha <= 1
    min_samples: int = 2

    def __post_init__(self) -> None:
        if not (0 < self.alpha <= 1.0):
            raise ValueError("alpha must be in range (0, 1]")
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")

    @classmethod
    def from_dict(cls, data: dict) -> "SmoothingConfig":
        return cls(
            alpha=data.get("alpha", 0.3),
            min_samples=data.get("min_samples", 2),
        )

    def to_dict(self) -> dict:
        return {"alpha": self.alpha, "min_samples": self.min_samples}


@dataclass
class SmoothedSeries:
    key: str
    values: List[float]
    smoothed: List[float]
    latest_raw: float
    latest_smoothed: float

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "latest_raw": self.latest_raw,
            "latest_smoothed": round(self.latest_smoothed, 6),
            "sample_count": len(self.values),
        }


@dataclass
class SmoothingResult:
    series: List[SmoothedSeries] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"series": [s.to_dict() for s in self.series]}


class MetricSmoother:
    def __init__(self, config: Optional[SmoothingConfig] = None) -> None:
        self._config = config or SmoothingConfig()
        self._ema_state: Dict[str, float] = {}

    def smooth(self, key: str, values: List[float]) -> Optional[SmoothedSeries]:
        if len(values) < self._config.min_samples:
            return None
        alpha = self._config.alpha
        ema = values[0]
        smoothed: List[float] = [ema]
        for v in values[1:]:
            ema = alpha * v + (1 - alpha) * ema
            smoothed.append(ema)
        self._ema_state[key] = ema
        return SmoothedSeries(
            key=key,
            values=list(values),
            smoothed=smoothed,
            latest_raw=values[-1],
            latest_smoothed=ema,
        )

    def smooth_all(
        self, series_map: Dict[str, List[float]]
    ) -> SmoothingResult:
        result = SmoothingResult()
        for key, values in series_map.items():
            s = self.smooth(key, values)
            if s is not None:
                result.series.append(s)
        return result

    def latest_smoothed(self, key: str) -> Optional[float]:
        return self._ema_state.get(key)
