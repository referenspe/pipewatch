"""Reaper: removes stale WatchTargets that have not reported within a deadline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


@dataclass
class ReaperConfig:
    stale_seconds: float = 120.0
    critical_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.stale_seconds <= 0:
            raise ValueError("stale_seconds must be positive")
        if self.critical_seconds <= self.stale_seconds:
            raise ValueError("critical_seconds must be greater than stale_seconds")

    @classmethod
    def from_dict(cls, data: dict) -> "ReaperConfig":
        return cls(
            stale_seconds=data.get("stale_seconds", 120.0),
            critical_seconds=data.get("critical_seconds", 300.0),
        )

    def to_dict(self) -> dict:
        return {
            "stale_seconds": self.stale_seconds,
            "critical_seconds": self.critical_seconds,
        }


@dataclass
class ReapResult:
    key: str
    last_seen: float
    age_seconds: float
    is_critical: bool

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "last_seen": self.last_seen,
            "age_seconds": round(self.age_seconds, 3),
            "is_critical": self.is_critical,
        }


class Reaper:
    def __init__(self, config: Optional[ReaperConfig] = None) -> None:
        self._config = config or ReaperConfig()
        self._registry: Dict[str, float] = {}

    def heartbeat(self, key: str, now: Optional[float] = None) -> None:
        self._registry[key] = now if now is not None else time.monotonic()

    def reap(self, now: Optional[float] = None) -> List[ReapResult]:
        ts = now if now is not None else time.monotonic()
        results: List[ReapResult] = []
        for key, last in list(self._registry.items()):
            age = ts - last
            if age >= self._config.stale_seconds:
                results.append(ReapResult(
                    key=key,
                    last_seen=last,
                    age_seconds=age,
                    is_critical=age >= self._config.critical_seconds,
                ))
        return results

    def remove(self, key: str) -> None:
        self._registry.pop(key, None)

    def keys(self) -> List[str]:
        return list(self._registry.keys())
