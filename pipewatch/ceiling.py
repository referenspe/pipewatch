"""Ceiling detector — flags metrics that are pegged at or near a maximum value."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


@dataclass
class CeilingConfig:
    """Configuration for ceiling detection."""

    # Fraction of the ceiling value that counts as "near" (0 < proximity < 1).
    proximity: float = 0.95
    # Minimum number of samples required before analysis is performed.
    min_samples: int = 3

    def __post_init__(self) -> None:
        if not (0.0 < self.proximity < 1.0):
            raise ValueError("proximity must be between 0 and 1 (exclusive)")
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")

    @classmethod
    def from_dict(cls, data: Dict) -> "CeilingConfig":
        return cls(
            proximity=data.get("proximity", 0.95),
            min_samples=data.get("min_samples", 3),
        )

    def to_dict(self) -> Dict:
        return {"proximity": self.proximity, "min_samples": self.min_samples}


@dataclass
class CeilingResult:
    """Result of a ceiling analysis for a single metric key."""

    key: str
    ceiling: float
    latest: float
    ratio: float  # latest / ceiling
    status: MetricStatus
    sample_count: int

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "ceiling": self.ceiling,
            "latest": self.latest,
            "ratio": round(self.ratio, 4),
            "status": self.status.value,
            "sample_count": self.sample_count,
        }


@dataclass
class CeilingDetector:
    """Detects metrics that are pegged at or near a known ceiling value."""

    config: CeilingConfig = field(default_factory=CeilingConfig)

    def analyse(self, key: str, history: MetricHistory, ceiling: float) -> Optional[CeilingResult]:
        """Return a CeilingResult or None if there are insufficient samples."""
        snapshots = history.all(key)
        if len(snapshots) < self.config.min_samples:
            return None

        latest = snapshots[-1].value
        if ceiling == 0.0:
            ratio = 0.0
        else:
            ratio = latest / ceiling

        if ratio >= 1.0:
            status = MetricStatus.CRITICAL
        elif ratio >= self.config.proximity:
            status = MetricStatus.WARNING
        else:
            status = MetricStatus.OK

        return CeilingResult(
            key=key,
            ceiling=ceiling,
            latest=latest,
            ratio=ratio,
            status=status,
            sample_count=len(snapshots),
        )

    def analyse_all(
        self, history: MetricHistory, ceilings: Dict[str, float]
    ) -> List[CeilingResult]:
        """Analyse all keys that have a configured ceiling value."""
        results: List[CeilingResult] = []
        for key, ceiling in ceilings.items():
            result = self.analyse(key, history, ceiling)
            if result is not None:
                results.append(result)
        return results
