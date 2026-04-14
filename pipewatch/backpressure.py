"""Backpressure detector: flags when a pipeline stage is processing
slower than it receives, based on queue-depth or lag metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BackpressureConfig:
    """Configuration for the backpressure detector."""
    warn_lag: float = 10.0       # lag (seconds or units) before WARNING
    critical_lag: float = 30.0  # lag before CRITICAL
    window: int = 5             # number of recent samples to consider

    def __post_init__(self) -> None:
        if self.warn_lag <= 0:
            raise ValueError("warn_lag must be positive")
        if self.critical_lag <= self.warn_lag:
            raise ValueError("critical_lag must be greater than warn_lag")
        if self.window < 1:
            raise ValueError("window must be at least 1")

    @classmethod
    def from_dict(cls, data: Dict) -> "BackpressureConfig":
        return cls(
            warn_lag=data.get("warn_lag", 10.0),
            critical_lag=data.get("critical_lag", 30.0),
            window=data.get("window", 5),
        )

    def to_dict(self) -> Dict:
        return {
            "warn_lag": self.warn_lag,
            "critical_lag": self.critical_lag,
            "window": self.window,
        }


@dataclass
class BackpressureResult:
    """Result of a backpressure evaluation for one pipeline stage."""
    stage: str
    avg_lag: float
    level: str          # "ok", "warning", "critical"
    sample_count: int

    def to_dict(self) -> Dict:
        return {
            "stage": self.stage,
            "avg_lag": round(self.avg_lag, 4),
            "level": self.level,
            "sample_count": self.sample_count,
        }


@dataclass
class BackpressureDetector:
    """Evaluates lag samples for a set of pipeline stages."""
    config: BackpressureConfig
    _buffers: Dict[str, List[float]] = field(default_factory=dict, init=False)

    def record(self, stage: str, lag: float) -> None:
        """Record a lag observation for *stage*."""
        buf = self._buffers.setdefault(stage, [])
        buf.append(lag)
        # keep only the most recent *window* samples
        if len(buf) > self.config.window:
            self._buffers[stage] = buf[-self.config.window :]

    def evaluate(self, stage: str) -> Optional[BackpressureResult]:
        """Return a BackpressureResult for *stage*, or None if no data."""
        buf = self._buffers.get(stage)
        if not buf:
            return None
        avg = sum(buf) / len(buf)
        if avg >= self.config.critical_lag:
            level = "critical"
        elif avg >= self.config.warn_lag:
            level = "warning"
        else:
            level = "ok"
        return BackpressureResult(
            stage=stage,
            avg_lag=avg,
            level=level,
            sample_count=len(buf),
        )

    def evaluate_all(self) -> List[BackpressureResult]:
        """Evaluate every stage that has recorded data."""
        return [r for s in list(self._buffers) if (r := self.evaluate(s))]
