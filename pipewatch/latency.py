"""Latency tracking and threshold evaluation for pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LatencyConfig:
    warn_ms: float = 500.0
    critical_ms: float = 2000.0
    window_size: int = 20

    def __post_init__(self) -> None:
        if self.warn_ms <= 0:
            raise ValueError("warn_ms must be positive")
        if self.critical_ms <= self.warn_ms:
            raise ValueError("critical_ms must be greater than warn_ms")
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")

    @classmethod
    def from_dict(cls, data: dict) -> "LatencyConfig":
        return cls(
            warn_ms=data.get("warn_ms", 500.0),
            critical_ms=data.get("critical_ms", 2000.0),
            window_size=int(data.get("window_size", 20)),
        )

    def to_dict(self) -> dict:
        return {
            "warn_ms": self.warn_ms,
            "critical_ms": self.critical_ms,
            "window_size": self.window_size,
        }


@dataclass
class LatencyResult:
    stage: str
    samples: List[float]
    avg_ms: float
    p95_ms: float
    is_warning: bool
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "avg_ms": round(self.avg_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
            "sample_count": len(self.samples),
        }


@dataclass
class LatencyTracker:
    config: LatencyConfig = field(default_factory=LatencyConfig)
    _windows: Dict[str, List[float]] = field(default_factory=dict, init=False)

    def record(self, stage: str, latency_ms: float) -> None:
        buf = self._windows.setdefault(stage, [])
        buf.append(latency_ms)
        if len(buf) > self.config.window_size:
            buf.pop(0)

    def evaluate(self, stage: str) -> Optional[LatencyResult]:
        samples = self._windows.get(stage)
        if not samples:
            return None
        sorted_samples = sorted(samples)
        avg = sum(sorted_samples) / len(sorted_samples)
        idx = max(0, int(len(sorted_samples) * 0.95) - 1)
        p95 = sorted_samples[idx]
        return LatencyResult(
            stage=stage,
            samples=list(samples),
            avg_ms=avg,
            p95_ms=p95,
            is_warning=avg >= self.config.warn_ms,
            is_critical=avg >= self.config.critical_ms,
        )

    def evaluate_all(self) -> List[LatencyResult]:
        return [r for s in self._windows if (r := self.evaluate(s)) is not None]
