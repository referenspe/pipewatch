"""Reporter for pipeline dependency analysis results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.dependency import DependencyResult


class DependencyReporter:
    def __init__(self, results: List[DependencyResult]) -> None:
        self._results = results

    def has_cycles(self) -> bool:
        return any(r.has_cycle for r in self._results)

    def has_missing(self) -> bool:
        return any(r.missing for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "No dependency data available."
        lines = ["=== Pipeline Dependency Report ==="]
        for r in self._results:
            status = "OK"
            if r.has_cycle:
                status = "CYCLE DETECTED"
            elif r.missing:
                status = f"MISSING: {', '.join(r.missing)}"
            dep_str = ", ".join(r.dependencies) if r.dependencies else "none"
            lines.append(
                f"  {r.stage} (depth={r.depth}) [{status}] depends_on=[{dep_str}]"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {
                "has_cycles": self.has_cycles(),
                "has_missing": self.has_missing(),
                "stages": [r.to_dict() for r in self._results],
            },
            indent=2,
        )
