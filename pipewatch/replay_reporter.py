"""Human-readable and JSON reporting for ReplayResult objects."""
from __future__ import annotations

import json
from typing import List

from pipewatch.replay import ReplayResult


class ReplayReporter:
    """Formats one or more ReplayResult objects for output."""

    def __init__(self, results: List[ReplayResult]) -> None:
        self.results = results

    def has_criticals(self) -> bool:
        return any(r.critical_count > 0 for r in self.results)

    def has_warnings(self) -> bool:
        return any(r.warning_count > 0 for r in self.results)

    def format_text(self) -> str:
        if not self.results:
            return "No replay results."

        lines: List[str] = []
        for result in self.results:
            lines.append(f"Replay: {result.key}")
            lines.append(f"  Snapshots evaluated : {result.total}")
            lines.append(f"  Critical            : {result.critical_count}")
            lines.append(f"  Warning             : {result.warning_count}")
            if result.stopped_early:
                lines.append("  [stopped early on first CRITICAL]")
            if result.events:
                lines.append("  Recent events:")
                for event in result.events[-3:]:
                    ts = event.snapshot.timestamp.isoformat()
                    status = event.metric.status.value
                    val = event.snapshot.value
                    lines.append(f"    {ts}  value={val:.4g}  status={status}")
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self.results], indent=2)
