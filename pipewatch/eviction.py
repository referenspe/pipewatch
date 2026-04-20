"""Eviction policy for removing low-priority or stale metrics from active tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EvictionConfig:
    max_keys: int = 100
    evict_after_seconds: int = 3600
    evict_on_ok_streak: int = 0  # 0 = disabled

    @classmethod
    def from_dict(cls, data: dict) -> "EvictionConfig":
        return cls(
            max_keys=data.get("max_keys", 100),
            evict_after_seconds=data.get("evict_after_seconds", 3600),
            evict_on_ok_streak=data.get("evict_on_ok_streak", 0),
        )

    def to_dict(self) -> dict:
        return {
            "max_keys": self.max_keys,
            "evict_after_seconds": self.evict_after_seconds,
            "evict_on_ok_streak": self.evict_on_ok_streak,
        }


@dataclass
class EvictionResult:
    key: str
    reason: str
    age_seconds: float
    ok_streak: int

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "reason": self.reason,
            "age_seconds": round(self.age_seconds, 3),
            "ok_streak": self.ok_streak,
        }


@dataclass
class Eviction:
    config: EvictionConfig = field(default_factory=EvictionConfig)
    _last_seen: Dict[str, float] = field(default_factory=dict, init=False)
    _ok_streaks: Dict[str, int] = field(default_factory=dict, init=False)

    def record(self, key: str, is_ok: bool, now: float) -> None:
        self._last_seen[key] = now
        if is_ok:
            self._ok_streaks[key] = self._ok_streaks.get(key, 0) + 1
        else:
            self._ok_streaks[key] = 0

    def evaluate(self, now: float) -> List[EvictionResult]:
        evicted: List[EvictionResult] = []
        keys = list(self._last_seen.keys())

        for key in keys:
            age = now - self._last_seen[key]
            streak = self._ok_streaks.get(key, 0)
            reason: Optional[str] = None

            if age >= self.config.evict_after_seconds:
                reason = "stale"
            elif (
                self.config.evict_on_ok_streak > 0
                and streak >= self.config.evict_on_ok_streak
            ):
                reason = "ok_streak"

            if reason:
                evicted.append(EvictionResult(key=key, reason=reason, age_seconds=age, ok_streak=streak))
                del self._last_seen[key]
                self._ok_streaks.pop(key, None)

        # enforce max_keys by evicting oldest first
        while len(self._last_seen) > self.config.max_keys:
            oldest = min(self._last_seen, key=lambda k: self._last_seen[k])
            age = now - self._last_seen[oldest]
            streak = self._ok_streaks.get(oldest, 0)
            evicted.append(EvictionResult(key=oldest, reason="capacity", age_seconds=age, ok_streak=streak))
            del self._last_seen[oldest]
            self._ok_streaks.pop(oldest, None)

        return evicted

    def active_keys(self) -> List[str]:
        return list(self._last_seen.keys())
