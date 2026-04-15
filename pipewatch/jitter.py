"""Jitter detection: flags metrics whose values fluctuate erratically."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory


@dataclass
class JitterConfig:
    """Configuration for jitter detection."""
    min_samples: int = 5
    warn_cv: float = 0.25   # coefficient of variation threshold for WARNING
    critical_cv: float = 0.50  # coefficient of variation threshold for CRITICAL

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be >= 2")
        if self.warn_cv <= 0:
            raise ValueError("warn_cv must be positive")
        if self.critical_cv <= self.warn_cv:
            raise ValueError("critical_cv must be greater than warn_cv")

    @classmethod
    def from_dict(cls, data: dict) -> "JitterConfig":
        return cls(
            min_samples=data.get("min_samples", 5),
            warn_cv=data.get("warn_cv", 0.25),
            critical_cv=data.get("critical_cv", 0.50),
        )

    def to_dict(self) -> dict:
        return {
            "min_samples": self.min_samples,
            "warn_cv": self.warn_cv,
            "critical_cv": self.critical_cv,
        }


@dataclass
class JitterResult:
    """Result of jitter analysis for a single metric key."""
    metric_key: str
    sample_count: int
    mean: float
    std_dev: float
    cv: float          # coefficient of variation  (std_dev / mean)
    level: str         # "ok", "warn", or "critical"

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "sample_count": self.sample_count,
            "mean": round(self.mean, 6),
            "std_dev": round(self.std_dev, 6),
            "cv": round(self.cv, 6),
            "level": self.level,
        }


@dataclass
class JitterDetector:
    """Detects high jitter in metric value series."""
    config: JitterConfig = field(default_factory=JitterConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[JitterResult]:
        """Return a JitterResult for *key*, or None if insufficient samples."""
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return None

        values = [s.value for s in snapshots]
        mean = sum(values) / len(values)
        if mean == 0:
            cv = 0.0
            std_dev = 0.0
        else:
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = variance ** 0.5
            cv = std_dev / abs(mean)

        if cv >= self.config.critical_cv:
            level = "critical"
        elif cv >= self.config.warn_cv:
            level = "warn"
        else:
            level = "ok"

        return JitterResult(
            metric_key=key,
            sample_count=len(values),
            mean=mean,
            std_dev=std_dev,
            cv=cv,
            level=level,
        )

    def analyse_all(
        self, history: MetricHistory, keys: List[str]
    ) -> Dict[str, JitterResult]:
        """Analyse jitter for every key in *keys*, skipping those with too few samples."""
        results: Dict[str, JitterResult] = {}
        for key in keys:
            result = self.analyse(key, history)
            if result is not None:
                results[key] = result
        return results
