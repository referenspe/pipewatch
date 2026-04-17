"""Reporter for Limiter results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.limiter import LimiterResult


class LimiterReporter:
    def __init__(self, results: List[LimiterResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def has_throttled(self) -> bool:
        return any(not r.allowed for r in self._results)

    def throttled_results(self) -> List[LimiterResult]:
        return [r for r in self._results if not r.allowed]

    def format_text(self) -> str:
        if not self._results:
            return "Limiter: no results."
        lines = ["Limiter Report:"]
        for r in self._results:
            status = "ALLOWED" if r.allowed else "THROTTLED"
            lines.append(
                f"  [{status}] {r.key}: {r.current_count}/{r.limit} events in window"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)
