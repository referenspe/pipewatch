"""High-watermark tracking for pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class WatermarkConfig:
    reset_on_critical: bool = False
    track_low: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "WatermarkConfig":
        return cls(
            reset_on_critical=data.get("reset_on_critical", False),
            track_low=data.get("track_low", True),
        )

    def to_dict(self) -> dict:
        return {"reset_on_critical": self.reset_on_critical, "track_low": self.track_low}


@dataclass
class WatermarkResult:
    key: str
    high: float
    low: Optional[float]
    current: float
    reset: bool = False

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "high": self.high,
            "low": self.low,
            "current": self.current,
            "reset": self.reset,
        }


@dataclass
class WatermarkTracker:
    config: WatermarkConfig = field(default_factory=WatermarkConfig)
    _highs: Dict[str, float] = field(default_factory=dict, init=False)
    _lows: Dict[str, float] = field(default_factory=dict, init=False)

    def evaluate(self, history: MetricHistory, key: str) -> Optional[WatermarkResult]:
        latest = history.latest(key)
        if latest is None:
            return None
        value = latest.value
        status = latest.status
        reset = False
        if self.config.reset_on_critical and status == MetricStatus.CRITICAL:
            self._highs.pop(key, None)
            self._lows.pop(key, None)
            reset = True
        high = max(self._highs.get(key, value), value)
        self._highs[key] = high
        low = None
        if self.config.track_low:
            low = min(self._lows.get(key, value), value)
            self._lows[key] = low
        return WatermarkResult(key=key, high=high, low=low, current=value, reset=reset)

    def evaluate_all(self, history: MetricHistory) -> Dict[str, WatermarkResult]:
        results = {}
        for key in history.keys():
            result = self.evaluate(history, key)
            if result is not None:
                results[key] = result
        return results
