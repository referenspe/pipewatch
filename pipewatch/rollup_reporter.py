"""Formats RollupResult objects as text or JSON."""
from __future__ import annotations

import json
from typing import List

from pipewatch.rollup import RollupResult


class RollupReporter:
    def __init__(self, results: List[RollupResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return any(r.windows for r in self._results)

    def format_text(self) -> str:
        if not self.has_results():
            return "No rollup windows available."

        lines: List[str] = ["=== Metric Rollup ==="]
        for result in self._results:
            if not result.windows:
                continue
            lines.append(f"  {result.metric_key}:")
            for w in result.windows:
                lines.append(
                    f"    [{w.start.strftime('%H:%M:%S')} – {w.end.strftime('%H:%M:%S')}] "
                    f"n={w.count}  mean={w.mean:.4f}  "
                    f"min={w.minimum:.4f}  max={w.maximum:.4f}"
                )
        return "\n".join(lines)

    def format_json(self) -> str:
        payload = [
            {
                "metric_key": r.metric_key,
                "windows": [w.to_dict() for w in r.windows],
            }
            for r in self._results
        ]
        return json.dumps(payload, indent=2)
