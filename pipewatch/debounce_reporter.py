"""Human-readable and JSON reporting for debounce results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.debounce import DebounceResult


class DebounceReporter:
    def __init__(self, results: List[DebounceResult]) -> None:
        self._results = results

    def has_fired(self) -> bool:
        return any(r.fired for r in self._results)

    def fired_results(self) -> List[DebounceResult]:
        return [r for r in self._results if r.fired]

    def format_text(self) -> str:
        if not self._results:
            return "Debounce: no results."
        lines = ["Debounce Report"]
        lines.append("-" * 32)
        for r in self._results:
            fired_label = "FIRED" if r.fired else "pending"
        lines.append(
                f"  {r.metric_key}: status={r.status.value}  "
                f"consecutive={r.consecutive}  [{fired_label}]"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)
