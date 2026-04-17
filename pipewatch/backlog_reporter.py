"""Reporter for backlog tracking results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.backlog import BacklogResult


class BacklogReporter:
    def __init__(self, results: List[BacklogResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def has_warnings(self) -> bool:
        return any(r.level == "warn" for r in self._results)

    def has_critical(self) -> bool:
        return any(r.level == "critical" for r in self._results)

    def has_growing(self) -> bool:
        return any(r.is_growing for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Backlog: no data recorded."
        lines = ["Backlog Report:"]
        for r in self._results:
            growing = " [GROWING]" if r.is_growing else ""
            lines.append(
                f"  {r.key}: depth={r.current_depth} level={r.level.upper()}{growing}"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)
