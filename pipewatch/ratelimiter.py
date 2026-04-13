"""Rate limiter for controlling how frequently alerts are emitted per metric key."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class RateLimiterConfig:
    """Configuration for the rate limiter."""

    min_interval_seconds: float = 60.0
    max_per_minute: int = 10

    def __post_init__(self) -> None:
        if self.min_interval_seconds <= 0:
            raise ValueError("min_interval_seconds must be positive")
        if self.max_per_minute < 1:
            raise ValueError("max_per_minute must be at least 1")

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimiterConfig":
        return cls(
            min_interval_seconds=float(data.get("min_interval_seconds", 60.0)),
            max_per_minute=int(data.get("max_per_minute", 10)),
        )

    def to_dict(self) -> dict:
        return {
            "min_interval_seconds": self.min_interval_seconds,
            "max_per_minute": self.max_per_minute,
        }


@dataclass
class _KeyState:
    last_sent: Optional[datetime] = None
    count_in_window: int = 0
    window_start: Optional[datetime] = None


@dataclass
class RateLimitResult:
    key: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict:
        return {"key": self.key, "allowed": self.allowed, "reason": self.reason}


class RateLimiter:
    """Tracks per-key emission state and enforces rate limits."""

    def __init__(self, config: Optional[RateLimiterConfig] = None) -> None:
        self._config = config or RateLimiterConfig()
        self._states: Dict[str, _KeyState] = {}

    def check(self, key: str, now: Optional[datetime] = None) -> RateLimitResult:
        """Return whether an alert for *key* is allowed at *now*."""
        now = now or datetime.now(tz=timezone.utc)
        state = self._states.setdefault(key, _KeyState())

        # Enforce minimum interval between consecutive alerts.
        if state.last_sent is not None:
            elapsed = (now - state.last_sent).total_seconds()
            if elapsed < self._config.min_interval_seconds:
                return RateLimitResult(key=key, allowed=False, reason="min_interval")

        # Enforce max-per-minute sliding window.
        if state.window_start is None or (now - state.window_start).total_seconds() >= 60:
            state.window_start = now
            state.count_in_window = 0

        if state.count_in_window >= self._config.max_per_minute:
            return RateLimitResult(key=key, allowed=False, reason="max_per_minute")

        # Allow — update state.
        state.last_sent = now
        state.count_in_window += 1
        return RateLimitResult(key=key, allowed=True, reason="ok")

    def reset(self, key: str) -> None:
        """Clear rate-limit state for *key*."""
        self._states.pop(key, None)
