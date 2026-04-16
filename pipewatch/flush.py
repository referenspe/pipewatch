"""Flush control: force-drain buffered metrics on demand or threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FlushConfig:
    max_buffer_size: int = 100
    flush_on_critical: bool = True
    auto_flush_interval: float = 60.0

    @staticmethod
    def from_dict(d: dict) -> "FlushConfig":
        return FlushConfig(
            max_buffer_size=d.get("max_buffer_size", 100),
            flush_on_critical=d.get("flush_on_critical", True),
            auto_flush_interval=d.get("auto_flush_interval", 60.0),
        )

    def to_dict(self) -> dict:
        return {
            "max_buffer_size": self.max_buffer_size,
            "flush_on_critical": self.flush_on_critical,
            "auto_flush_interval": self.auto_flush_interval,
        }


@dataclass
class FlushResult:
    flushed_count: int
    remaining_count: int
    triggered_by: str  # "manual", "threshold", "critical", "interval"

    def to_dict(self) -> dict:
        return {
            "flushed_count": self.flushed_count,
            "remaining_count": self.remaining_count,
            "triggered_by": self.triggered_by,
        }


@dataclass
class FlushBuffer:
    config: FlushConfig = field(default_factory=FlushConfig)
    _buffer: List[dict] = field(default_factory=list, init=False, repr=False)

    def push(self, item: dict) -> FlushResult | None:
        self._buffer.append(item)
        is_critical = item.get("status") == "critical"
        if self.config.flush_on_critical and is_critical:
            return self.flush(triggered_by="critical")
        if len(self._buffer) >= self.config.max_buffer_size:
            return self.flush(triggered_by="threshold")
        return None

    def flush(self, triggered_by: str = "manual") -> FlushResult:
        count = len(self._buffer)
        self._buffer.clear()
        return FlushResult(
            flushed_count=count,
            remaining_count=0,
            triggered_by=triggered_by,
        )

    @property
    def size(self) -> int:
        return len(self._buffer)

    def drain(self) -> List[dict]:
        items = list(self._buffer)
        self._buffer.clear()
        return items
