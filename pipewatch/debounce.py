"""Debounce: suppress alerts until a condition persists for N consecutive checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from pipewatch.metrics import MetricStatus


@dataclass
class DebounceConfig:
    """Configuration for the debounce filter."""
    min_consecutive: int = 2  # fires only after this many consecutive non-OK checks
    reset_on_ok: bool = True  # reset counter when metric returns to OK

    @classmethod
    def from_dict(cls, data: dict) -> "DebounceConfig":
        return cls(
            min_consecutive=int(data.get("min_consecutive", 2)),
            reset_on_ok=bool(data.get("reset_on_ok", True)),
        )

    def to_dict(self) -> dict:
        return {
            "min_consecutive": self.min_consecutive,
            "reset_on_ok": self.reset_on_ok,
        }


@dataclass
class DebounceResult:
    """Outcome of a single debounce evaluation."""
    metric_key: str
    status: MetricStatus
    consecutive: int
    fired: bool  # True when the alert should actually be emitted

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "status": self.status.value,
            "consecutive": self.consecutive,
            "fired": self.fired,
        }


@dataclass
class _DebounceState:
    consecutive: int = 0
    last_status: Optional[MetricStatus] = None


class Debouncer:
    """Tracks consecutive non-OK occurrences and decides whether to fire."""

    def __init__(self, config: Optional[DebounceConfig] = None) -> None:
        self._config = config or DebounceConfig()
        self._states: Dict[str, _DebounceState] = {}

    def evaluate(self, metric_key: str, status: MetricStatus) -> DebounceResult:
        state = self._states.setdefault(metric_key, _DebounceState())

        if status == MetricStatus.OK:
            if self._config.reset_on_ok:
                state.consecutive = 0
            state.last_status = status
            return DebounceResult(
                metric_key=metric_key,
                status=status,
                consecutive=state.consecutive,
                fired=False,
            )

        state.consecutive += 1
        state.last_status = status
        fired = state.consecutive >= self._config.min_consecutive
        return DebounceResult(
            metric_key=metric_key,
            status=status,
            consecutive=state.consecutive,
            fired=fired,
        )

    def reset(self, metric_key: str) -> None:
        """Manually reset the counter for a given key."""
        self._states.pop(metric_key, None)
