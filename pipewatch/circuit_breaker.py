"""Circuit breaker for suppressing checks on repeatedly failing targets."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional


class BreakerState(str, Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # checks suppressed
    HALF_OPEN = "half_open"  # one probe allowed


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5        # consecutive failures before opening
    recovery_timeout: int = 60        # seconds before moving to half-open
    success_threshold: int = 2        # successes in half-open to close again

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitBreakerConfig":
        return cls(
            failure_threshold=data.get("failure_threshold", 5),
            recovery_timeout=data.get("recovery_timeout", 60),
            success_threshold=data.get("success_threshold", 2),
        )

    def to_dict(self) -> dict:
        return {
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "success_threshold": self.success_threshold,
        }


@dataclass
class _BreakerEntry:
    state: BreakerState = BreakerState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    opened_at: Optional[datetime] = None


@dataclass
class BreakerResult:
    key: str
    state: BreakerState
    allowed: bool

    def to_dict(self) -> dict:
        return {"key": self.key, "state": self.state.value, "allowed": self.allowed}


class CircuitBreaker:
    def __init__(self, config: Optional[CircuitBreakerConfig] = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._entries: Dict[str, _BreakerEntry] = {}

    def _entry(self, key: str) -> _BreakerEntry:
        if key not in self._entries:
            self._entries[key] = _BreakerEntry()
        return self._entries[key]

    def is_allowed(self, key: str, now: Optional[datetime] = None) -> BreakerResult:
        now = now or datetime.utcnow()
        entry = self._entry(key)
        if entry.state == BreakerState.CLOSED:
            return BreakerResult(key, BreakerState.CLOSED, True)
        if entry.state == BreakerState.OPEN:
            elapsed = (now - entry.opened_at).total_seconds()  # type: ignore[operator]
            if elapsed >= self._config.recovery_timeout:
                entry.state = BreakerState.HALF_OPEN
                entry.consecutive_successes = 0
                return BreakerResult(key, BreakerState.HALF_OPEN, True)
            return BreakerResult(key, BreakerState.OPEN, False)
        # HALF_OPEN — allow the probe
        return BreakerResult(key, BreakerState.HALF_OPEN, True)

    def record_success(self, key: str) -> None:
        entry = self._entry(key)
        if entry.state == BreakerState.HALF_OPEN:
            entry.consecutive_successes += 1
            if entry.consecutive_successes >= self._config.success_threshold:
                entry.state = BreakerState.CLOSED
                entry.consecutive_failures = 0
        elif entry.state == BreakerState.CLOSED:
            entry.consecutive_failures = 0

    def record_failure(self, key: str, now: Optional[datetime] = None) -> None:
        now = now or datetime.utcnow()
        entry = self._entry(key)
        if entry.state == BreakerState.HALF_OPEN:
            entry.state = BreakerState.OPEN
            entry.opened_at = now
            entry.consecutive_successes = 0
            return
        entry.consecutive_failures += 1
        if entry.consecutive_failures >= self._config.failure_threshold:
            entry.state = BreakerState.OPEN
            entry.opened_at = now
