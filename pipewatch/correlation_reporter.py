"""Formatting helpers for correlation analysis results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.correlation import CorrelationResult, CorrelationStrength

_STRENGTH_LABEL: dict = {
    CorrelationStrength.STRONG: "strong",
    CorrelationStrength.MODERATE: "moderate",
    CorrelationStrength.WEAK: "weak",
    CorrelationStrength.NONE: "none",
}


class CorrelationReporter:
    def __init__(self, results: List[CorrelationResult]) -> None:
        self._results = results

    def format_text(self) -> str:
        if not self._results:
            return "No correlation data available."
        lines = ["Metric Correlations:", "-" * 40]
        for r in self._results:
            sign = "+" if r.coefficient >= 0 else ""
            label = _STRENGTH_LABEL[r.strength]
            lines.append(
                f"  {r.key_a} <-> {r.key_b}: "
                f"r={sign}{r.coefficient:.4f} ({label}, n={r.sample_count})"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)

    def has_strong(self) -> bool:
        return any(r.strength == CorrelationStrength.STRONG for r in self._results)

    def strong_pairs(self) -> List[CorrelationResult]:
        return [r for r in self._results if r.strength == CorrelationStrength.STRONG]
