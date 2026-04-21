"""Fanout: broadcast a single metric event to multiple named channels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FanoutConfig:
    """Configuration for the fanout broadcaster."""
    channels: List[str] = field(default_factory=list)
    stop_on_error: bool = False
    max_channels: int = 16

    def __post_init__(self) -> None:
        if self.max_channels < 1:
            raise ValueError("max_channels must be at least 1")
        if len(self.channels) > self.max_channels:
            raise ValueError(
                f"channel count {len(self.channels)} exceeds max_channels {self.max_channels}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "FanoutConfig":
        return cls(
            channels=list(data.get("channels", [])),
            stop_on_error=bool(data.get("stop_on_error", False)),
            max_channels=int(data.get("max_channels", 16)),
        )

    def to_dict(self) -> dict:
        return {
            "channels": list(self.channels),
            "stop_on_error": self.stop_on_error,
            "max_channels": self.max_channels,
        }


@dataclass
class FanoutResult:
    """Result of a single fanout dispatch."""
    metric_key: str
    sent: List[str] = field(default_factory=list)
    failed: Dict[str, str] = field(default_factory=dict)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed)

    @property
    def total_sent(self) -> int:
        return len(self.sent)

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "sent": list(self.sent),
            "failed": dict(self.failed),
            "total_sent": self.total_sent,
            "has_failures": self.has_failures,
        }


class Fanout:
    """Broadcasts a metric event to multiple registered channels."""

    def __init__(self, config: Optional[FanoutConfig] = None) -> None:
        self._config = config or FanoutConfig()
        self._handlers: Dict[str, callable] = {}

    def register(self, name: str, handler: callable) -> None:
        """Register a callable handler under *name*."""
        if len(self._handlers) >= self._config.max_channels:
            raise RuntimeError(
                f"Cannot register '{name}': max_channels ({self._config.max_channels}) reached"
            )
        self._handlers[name] = handler

    def dispatch(self, metric_key: str, payload: dict) -> FanoutResult:
        """Send *payload* to all registered (or configured) channels."""
        targets = self._config.channels or list(self._handlers.keys())
        result = FanoutResult(metric_key=metric_key)
        for name in targets:
            handler = self._handlers.get(name)
            if handler is None:
                result.failed[name] = "handler not registered"
                if self._config.stop_on_error:
                    break
                continue
            try:
                handler(payload)
                result.sent.append(name)
            except Exception as exc:  # noqa: BLE001
                result.failed[name] = str(exc)
                if self._config.stop_on_error:
                    break
        return result
