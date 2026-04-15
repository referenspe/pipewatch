"""Cooldown tracker — prevents repeated alerts for the same metric within a quiet period."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class CooldownConfig:
    default_seconds: int = 300
    per_key: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownConfig":
        return cls(
            default_seconds=data.get("default_seconds", 300),
            per_key=data.get("per_key", {}),
        )

    def to_dict(self) -> dict:
        return {
            "default_seconds": self.default_seconds,
            "per_key": dict(self.per_key),
        }

    def seconds_for(self, key: str) -> int:
        return self.per_key.get(key, self.default_seconds)


@dataclass
class CooldownResult:
    key: str
    suppressed: bool
    remaining_seconds: float
    next_allowed: Optional[datetime]

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "suppressed": self.suppressed,
            "remaining_seconds": round(self.remaining_seconds, 2),
            "next_allowed": self.next_allowed.isoformat() if self.next_allowed else None,
        }


class CooldownTracker:
    """Tracks per-key cooldown windows and reports whether an alert should be suppressed."""

    def __init__(self, config: CooldownConfig) -> None:
        self._config = config
        self._last_sent: Dict[str, datetime] = {}

    def check(self, key: str, now: Optional[datetime] = None) -> CooldownResult:
        """Return a CooldownResult indicating whether *key* is currently suppressed."""
        now = now or datetime.utcnow()
        seconds = self._config.seconds_for(key)
        last = self._last_sent.get(key)

        if last is None:
            return CooldownResult(key=key, suppressed=False, remaining_seconds=0.0, next_allowed=None)

        next_allowed = last + timedelta(seconds=seconds)
        remaining = (next_allowed - now).total_seconds()

        if remaining > 0:
            return CooldownResult(key=key, suppressed=True, remaining_seconds=remaining, next_allowed=next_allowed)

        return CooldownResult(key=key, suppressed=False, remaining_seconds=0.0, next_allowed=next_allowed)

    def record(self, key: str, now: Optional[datetime] = None) -> None:
        """Record that an alert was sent for *key* at *now*."""
        self._last_sent[key] = now or datetime.utcnow()

    def reset(self, key: str) -> None:
        """Clear the cooldown for *key*."""
        self._last_sent.pop(key, None)

    def active_keys(self) -> list:
        return list(self._last_sent.keys())
