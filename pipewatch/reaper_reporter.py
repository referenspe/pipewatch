"""Reporter for Reaper stale-target results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.reaper import ReapResult


class ReaperReporter:
    def __init__(self, results: List[ReapResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def has_critical(self) -> bool:
        return any(r.is_critical for r in self._results)

    def has_stale(self) -> bool:
        return any(not r.is_critical for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Reaper: no stale targets detected."
        lines = ["Reaper stale targets:"]
        for r in self._results:
            label = "CRITICAL" if r.is_critical else "STALE"
            lines.append(f"  [{label}] {r.key} — age {r.age_seconds:.1f}s")
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)
