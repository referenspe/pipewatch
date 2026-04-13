"""Human-readable and JSON reporting for CheckpointTracker results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.checkpoint import CheckpointResult


class CheckpointReporter:
    def __init__(self, results: List[CheckpointResult]) -> None:
        self._results = results

    def has_stalls(self) -> bool:
        return any(r.stalled for r in self._results)

    def has_regressions(self) -> bool:
        return any(r.regressed for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Checkpoints: no results available."
        lines = ["Checkpoint Report"]
        lines.append("-" * 36)
        for r in self._results:
            flags: List[str] = []
            if r.stalled:
                flags.append("STALLED")
            if r.regressed:
                flags.append("REGRESSED")
            status = ", ".join(flags) if flags else "OK"
            lines.append(
                f"  {r.stage}: pos={r.current_position}  "
                f"age={r.seconds_since_update:.1f}s  [{status}]"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)
