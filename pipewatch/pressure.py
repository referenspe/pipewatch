"""Pressure monitor: tracks metric value rate-of-change and flags
rapid increases that may indicate a system under stress."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class PressureConfig:
    """Configuration for the pressure monitor."""
    min_samples: int = 3
    warn_rate: float = 0.10   # 10% rise per sample triggers WARNING
    critical_rate: float = 0.25  # 25% rise per sample triggers CRITICAL

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        if self.warn_rate <= 0:
            raise ValueError("warn_rate must be positive")
        if self.critical_rate <= self.warn_rate:
            raise ValueError("critical_rate must be greater than warn_rate")

    @classmethod
    def from_dict(cls, data: dict) -> "PressureConfig":
        return cls(
            min_samples=data.get("min_samples", 3),
            warn_rate=data.get("warn_rate", 0.10),
            critical_rate=data.get("critical_rate", 0.25),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "warn_rate": self.warn_rate,
            "critical_rate": self.critical_rate,
        }


@dataclass
class PressureResult:
    """Result of a pressure analysis for one metric key."""
    key: str
    status: MetricStatus
    avg_rate: float          # average per-step relative change
    sample_count: int
    message: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "status": self.status.value,
            "avg_rate": round(self.avg_rate, 6),
            "sample_count": self.sample_count,
            "message": self.message,
        }


@dataclass
class PressureMonitor:
    """Analyses metric histories for pressure (rapid value increases)."""
    config: PressureConfig = field(default_factory=PressureConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[PressureResult]:
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return None

        values = [s.value for s in snapshots]
        rates: list[float] = []
        for prev, curr in zip(values, values[1:]):
            if prev == 0:
                continue
            rates.append((curr - prev) / abs(prev))

        if not rates:
            return None

        avg_rate = sum(rates) / len(rates)

        if avg_rate >= self.config.critical_rate:
            status = MetricStatus.CRITICAL
            message = f"avg rate-of-change {avg_rate:.2%} exceeds critical threshold"
        elif avg_rate >= self.config.warn_rate:
            status = MetricStatus.WARNING
            message = f"avg rate-of-change {avg_rate:.2%} exceeds warning threshold"
        else:
            status = MetricStatus.OK
            message = f"avg rate-of-change {avg_rate:.2%} within normal range"

        return PressureResult(
            key=key,
            status=status,
            avg_rate=avg_rate,
            sample_count=len(snapshots),
            message=message,
        )

    def analyse_all(
        self, history: MetricHistory
    ) -> dict[str, PressureResult]:
        results: dict[str, PressureResult] = {}
        for key in history.keys():
            result = self.analyse(key, history)
            if result is not None:
                results[key] = result
        return results
