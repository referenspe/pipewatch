"""Reporter for FlushBuffer results."""
from __future__ import annotations

from typing import List

from pipewatch.flush import FlushResult


class FlushReporter:
    def __init__(self, results: List[FlushResult]) -> None:
        self._results = results

    @property
    def has_results(self) -> bool:
        return bool(self._results)

    @property
    def total_flushed(self) -> int:
        return sum(r.flushed_count for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "No flush events recorded."
        lines = ["Flush Events:"]
        for r in self._results:
            lines.append(
                f"  [{r.triggered_by}] flushed={r.flushed_count} remaining={r.remaining_count}"
            )
        lines.append(f"  Total flushed: {self.total_flushed}")
        return "\n".join(lines)

    def format_json(self) -> list:
        return [r.to_dict() for r in self._results]
