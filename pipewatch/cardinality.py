"""Cardinality tracking — monitors the number of distinct values for a metric key."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory


@dataclass
class CardinalityConfig:
    warn_above: int = 100
    critical_above: int = 500
    window_size: int = 1000  # number of recent snapshots to consider

    def __post_init__(self) -> None:
        if self.warn_above < 1:
            raise ValueError("warn_above must be at least 1")
        if self.critical_above <= self.warn_above:
            raise ValueError("critical_above must be greater than warn_above")
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")

    @classmethod
    def from_dict(cls, data: dict) -> "CardinalityConfig":
        return cls(
            warn_above=data.get("warn_above", 100),
            critical_above=data.get("critical_above", 500),
            window_size=data.get("window_size", 1000),
        )

    def to_dict(self) -> dict:
        return {
            "warn_above": self.warn_above,
            "critical_above": self.critical_above,
            "window_size": self.window_size,
        }


@dataclass
class CardinalityResult:
    key: str
    distinct_count: int
    is_warning: bool
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "distinct_count": self.distinct_count,
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
        }


@dataclass
class CardinalityAnalyser:
    config: CardinalityConfig = field(default_factory=CardinalityConfig)

    def analyse(self, key: str, history: MetricHistory) -> Optional[CardinalityResult]:
        snapshots = history.all()
        if not snapshots:
            return None
        recent = snapshots[-self.config.window_size :]
        distinct: set = {s.value for s in recent}
        count = len(distinct)
        return CardinalityResult(
            key=key,
            distinct_count=count,
            is_warning=self.config.warn_above < count <= self.config.critical_above,
            is_critical=count > self.config.critical_above,
        )

    def analyse_all(
        self, histories: Dict[str, MetricHistory]
    ) -> List[CardinalityResult]:
        results: List[CardinalityResult] = []
        for key, history in histories.items():
            result = self.analyse(key, history)
            if result is not None:
                results.append(result)
        return results
