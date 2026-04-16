"""Point-in-time snapshot capture for pipeline metrics."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pipewatch.metrics import PipelineMetric, MetricStatus


@dataclass
class SnapshotConfig:
    label: str = "default"
    include_ok: bool = True
    max_entries: int = 500

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotConfig":
        return cls(
            label=data.get("label", "default"),
            include_ok=data.get("include_ok", True),
            max_entries=int(data.get("max_entries", 500)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "include_ok": self.include_ok,
            "max_entries": self.max_entries,
        }


@dataclass
class SnapshotEntry:
    metric_key: str
    value: float
    status: MetricStatus
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "value": self.value,
            "status": self.status.value,
            "captured_at": self.captured_at.isoformat(),
        }


@dataclass
class SnapshotResult:
    label: str
    entries: list[SnapshotEntry]
    taken_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "taken_at": self.taken_at.isoformat(),
            "entries": [e.to_dict() for e in self.entries],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class SnapshotCapture:
    def __init__(self, config: SnapshotConfig | None = None) -> None:
        self._config = config or SnapshotConfig()

    def capture(self, metrics: list[PipelineMetric]) -> SnapshotResult:
        entries: list[SnapshotEntry] = []
        for m in metrics:
            if not self._config.include_ok and m.status == MetricStatus.OK:
                continue
            entries.append(SnapshotEntry(
                metric_key=m.key,
                value=m.value,
                status=m.status,
            ))
            if len(entries) >= self._config.max_entries:
                break
        return SnapshotResult(label=self._config.label, entries=entries)
