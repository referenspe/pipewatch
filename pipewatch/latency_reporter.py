"""Text and JSON reporting for latency tracking results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.latency import LatencyResult


class LatencyReporter:
    def __init__(self, results: List[LatencyResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def has_warnings(self) -> bool:
        return any(r.is_warning and not r.is_critical for r in self._results)

    def has_criticals(self) -> bool:
        return any(r.is_critical for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Latency: no data recorded."
        lines = ["Latency Report"]
        lines.append("-" * 30)
        for r in self._results:
            if r.is_critical:
                label = "CRITICAL"
            elif r.is_warning:
                label = "WARNING"
            else:
                label = "OK"
            lines.append(
                f"  [{label}] {r.stage}: avg={r.avg_ms:.1f}ms  p95={r.p95_ms:.1f}ms  n={len(r.samples)}"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {"latency": [r.to_dict() for r in self._results]},
            indent=2,
        )
