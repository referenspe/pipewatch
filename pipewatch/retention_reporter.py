"""Human-readable and JSON reporting for retention pruning results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.retention import RetentionResult


class RetentionReporter:
    """Formats a list of RetentionResult objects for output."""

    def __init__(self, results: List[RetentionResult]) -> None:
        self._results = results

    def has_removals(self) -> bool:
        """Return True if any pruning actually removed snapshots."""
        return any(r.removed_count > 0 for r in self._results)

    def total_removed(self) -> int:
        return sum(r.removed_count for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Retention: no histories to prune."

        lines = ["Retention pruning summary:", ""]
        for r in self._results:
            lines.append(
                f"  {r.metric_key}: removed {r.removed_count}, "
                f"remaining {r.remaining_count}"
            )
        lines.append("")
        lines.append(f"Total removed: {self.total_removed()}")
        return "\n".join(lines)

    def format_json(self) -> str:
        payload = {
            "total_removed": self.total_removed(),
            "results": [r.to_dict() for r in self._results],
        }
        return json.dumps(payload, indent=2)
