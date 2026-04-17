"""Backlog tracking: monitor queue depth and flag growing backlogs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BacklogConfig:
    warn_depth: int = 100
    critical_depth: int = 500
    window_size: int = 5

    def __post_init__(self) -> None:
        if self.warn_depth < 1:
            raise ValueError("warn_depth must be >= 1")
        if self.critical_depth <= self.warn_depth:
            raise ValueError("critical_depth must be greater than warn_depth")
        if self.window_size < 1:
            raise ValueError("window_size must be >= 1")

    @classmethod
    def from_dict(cls, data: dict) -> "BacklogConfig":
        return cls(
            warn_depth=data.get("warn_depth", 100),
            critical_depth=data.get("critical_depth", 500),
            window_size=data.get("window_size", 5),
        )

    def to_dict(self) -> dict:
        return {
            "warn_depth": self.warn_depth,
            "critical_depth": self.critical_depth,
            "window_size": self.window_size,
        }


@dataclass
class BacklogResult:
    key: str
    depths: List[int]
    current_depth: int
    is_growing: bool
    level: str  # "ok", "warn", "critical"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "current_depth": self.current_depth,
            "is_growing": self.is_growing,
            "level": self.level,
        }


@dataclass
class BacklogTracker:
    config: BacklogConfig
    _history: Dict[str, List[int]] = field(default_factory=dict)

    def record(self, key: str, depth: int) -> None:
        bucket = self._history.setdefault(key, [])
        bucket.append(depth)
        if len(bucket) > self.config.window_size:
            bucket.pop(0)

    def evaluate(self, key: str) -> Optional[BacklogResult]:
        depths = self._history.get(key)
        if not depths:
            return None
        current = depths[-1]
        is_growing = len(depths) >= 2 and depths[-1] > depths[-2]
        if current >= self.config.critical_depth:
            level = "critical"
        elif current >= self.config.warn_depth:
            level = "warn"
        else:
            level = "ok"
        return BacklogResult(
            key=key,
            depths=list(depths),
            current_depth=current,
            is_growing=is_growing,
            level=level,
        )

    def evaluate_all(self) -> List[BacklogResult]:
        results = []
        for key in self._history:
            r = self.evaluate(key)
            if r is not None:
                results.append(r)
        return results
