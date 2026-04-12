"""Alert suppressor: skip repeated identical alerts within a time window."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from pipewatch.alerts import AlertEvent


@dataclass
class SuppressorConfig:
    """Configuration for the alert suppressor."""

    window_seconds: int = 300  # suppress duplicates within this window
    max_suppressed: int = 10   # max alerts to suppress before forcing one through

    @classmethod
    def from_dict(cls, data: dict) -> "SuppressorConfig":
        return cls(
            window_seconds=data.get("window_seconds", 300),
            max_suppressed=data.get("max_suppressed", 10),
        )

    def to_dict(self) -> dict:
        return {
            "window_seconds": self.window_seconds,
            "max_suppressed": self.max_suppressed,
        }


@dataclass
class _SuppressState:
    last_sent: datetime
    suppressed_count: int = 0


@dataclass
class SuppressResult:
    event: AlertEvent
    suppressed: bool
    suppressed_count: int = 0

    def __str__(self) -> str:
        if self.suppressed:
            return f"[SUPPRESSED x{self.suppressed_count}] {self.event}"
        return str(self.event)


class Suppressor:
    """Prevents duplicate alerts from flooding channels."""

    def __init__(self, config: Optional[SuppressorConfig] = None) -> None:
        self._config = config or SuppressorConfig()
        self._state: Dict[str, _SuppressState] = {}

    def _key(self, event: AlertEvent) -> str:
        return f"{event.metric.key}:{event.metric.status.name}"

    def evaluate(
        self, event: AlertEvent, now: Optional[datetime] = None
    ) -> SuppressResult:
        """Return a SuppressResult indicating whether the event should be sent."""
        now = now or datetime.utcnow()
        key = self._key(event)
        window = timedelta(seconds=self._config.window_seconds)

        if key not in self._state:
            self._state[key] = _SuppressState(last_sent=now)
            return SuppressResult(event=event, suppressed=False)

        state = self._state[key]
        age = now - state.last_sent

        if age >= window or state.suppressed_count >= self._config.max_suppressed:
            suppressed_count = state.suppressed_count
            self._state[key] = _SuppressState(last_sent=now)
            return SuppressResult(
                event=event, suppressed=False, suppressed_count=suppressed_count
            )

        state.suppressed_count += 1
        return SuppressResult(
            event=event, suppressed=True, suppressed_count=state.suppressed_count
        )

    def reset(self, key: Optional[str] = None) -> None:
        """Clear suppression state for a key, or all keys if none given."""
        if key is None:
            self._state.clear()
        else:
            self._state.pop(key, None)
