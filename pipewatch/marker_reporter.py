"""Reporter for Marker results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.marker import MarkerEvent, MarkerResult


class MarkerReporter:
    def __init__(self, result: MarkerResult) -> None:
        self._result = result

    @property
    def has_results(self) -> bool:
        return bool(self._result.events)

    @property
    def total_marks(self) -> int:
        return sum(e.count for e in self._result.events)

    def top(self, n: int = 5) -> List[MarkerEvent]:
        """Return the top-n markers by count."""
        return sorted(self._result.events, key=lambda e: e.count, reverse=True)[:n]

    def format_text(self) -> str:
        if not self.has_results:
            return "No markers recorded."
        lines = ["Markers:"]
        for event in self._result.events:
            lines.append(f"  [{event.key}] {event.label}  (hits: {event.count})")
        lines.append(f"Total hits: {self.total_marks}")
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(self._result.to_dict(), indent=2)
