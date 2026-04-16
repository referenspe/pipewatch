"""Reporting helpers for snapshot results."""
from __future__ import annotations

import json
from pipewatch.snapshot import SnapshotResult
from pipewatch.metrics import MetricStatus


class SnapshotReporter:
    def __init__(self, result: SnapshotResult) -> None:
        self._result = result

    def has_entries(self) -> bool:
        return bool(self._result.entries)

    def has_critical(self) -> bool:
        return any(e.status == MetricStatus.CRITICAL for e in self._result.entries)

    def has_warnings(self) -> bool:
        return any(e.status == MetricStatus.WARNING for e in self._result.entries)

    def format_text(self) -> str:
        r = self._result
        if not r.entries:
            return f"[Snapshot:{r.label}] No entries captured."
        lines = [f"[Snapshot:{r.label}] taken at {r.taken_at.isoformat()}"]
        for e in r.entries:
            lines.append(f"  {e.metric_key}: {e.value:.4g} [{e.status.value.upper()}]")
        return "\n".join(lines)

    def format_json(self) -> str:
        return self._result.to_json()
