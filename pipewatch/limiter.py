"""Per-key metric rate limiting with sliding window counters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
import time


@dataclass
class LimiterConfig:
    max_events: int = 10
    window_seconds: float = 60.0

    @classmethod
    def from_dict(cls, data: dict) -> "LimiterConfig":
        return cls(
            max_events=data.get("max_events", 10),
            window_seconds=data.get("window_seconds", 60.0),
        )

    def to_dict(self) -> dict:
        return {"max_events": self.max_events, "window_seconds": self.window_seconds}


@dataclass
class LimiterResult:
    key: str
    allowed: bool
    current_count: int
    limit: int

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "allowed": self.allowed,
            "current_count": self.current_count,
            "limit": self.limit,
        }


@dataclass
class _KeyWindow:
    timestamps: List[float] = field(default_factory=list)

    def prune(self, cutoff: float) -> None:
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count(self) -> int:
        return len(self.timestamps)

    def record(self, now: float) -> None:
        self.timestamps.append(now)


class Limiter:
    def __init__(self, config: LimiterConfig | None = None) -> None:
        self._config = config or LimiterConfig()
        self._windows: Dict[str, _KeyWindow] = {}

    def check(self, key: str, now: float | None = None) -> LimiterResult:
        if now is None:
            now = time.monotonic()
        cutoff = now - self._config.window_seconds
        window = self._windows.setdefault(key, _KeyWindow())
        window.prune(cutoff)
        allowed = window.count() < self._config.max_events
        if allowed:
            window.record(now)
        return LimiterResult(
            key=key,
            allowed=allowed,
            current_count=window.count(),
            limit=self._config.max_events,
        )

    def reset(self, key: str) -> None:
        self._windows.pop(key, None)

    def reset_all(self) -> None:
        self._windows.clear()
