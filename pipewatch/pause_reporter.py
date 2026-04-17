"""Reporter for PauseController results."""
from __future__ import annotations

from typing import List

from pipewatch.pause import PauseResult


class PauseReporter:
    def __init__(self, results: List[PauseResult]) -> None:
        self._results = results

    def has_paused(self) -> bool:
        return any(r.paused for r in self._results)

    def has_auto_resumed(self) -> bool:
        return any(r.auto_resumed for r in self._results)

    def paused_results(self) -> List[PauseResult]:
        return [r for r in self._results if r.paused]

    def format_text(self) -> str:
        if not self._results:
            return "No pause state recorded."
        lines = ["Pause Report:", "-" * 30]
        for r in self._results:
            status = "PAUSED" if r.paused else "ACTIVE"
            extra = " (auto-resumed)" if r.auto_resumed else ""
            paused_str = r.paused_at.isoformat() if r.paused_at else "n/a"
            lines.append(f"  [{status}] {r.key}{extra} | paused_at={paused_str}")
        return "\n".join(lines)

    def format_json(self) -> list:
        return [r.to_dict() for r in self._results]
