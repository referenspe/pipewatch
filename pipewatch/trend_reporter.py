"""Formats trend analysis results for CLI output."""

from __future__ import annotations

import json
from typing import List

from pipewatch.trend import TrendDirection, TrendResult

_ICONS: dict[TrendDirection, str] = {
    TrendDirection.RISING: "↑",
    TrendDirection.FALLING: "↓",
    TrendDirection.STABLE: "→",
    TrendDirection.UNKNOWN: "?",
}


class TrendReporter:
    """Renders a list of TrendResult objects as text or JSON."""

    def format_text(self, results: List[TrendResult]) -> str:
        if not results:
            return "No trend data available."
        lines = ["Trend Analysis", "-" * 30]
        for r in results:
            icon = _ICONS[r.direction]
            slope_str = f"{r.slope:+.4f}" if r.slope is not None else "n/a"
            lines.append(
                f"  {icon}  {r.key:<20} {r.direction.value:<8}  slope={slope_str}  samples={r.sample_count}"
            )
        return "\n".join(lines)

    def format_json(self, results: List[TrendResult]) -> str:
        return json.dumps([r.to_dict() for r in results], indent=2)

    def has_rising(self, results: List[TrendResult]) -> bool:
        return any(r.direction == TrendDirection.RISING for r in results)

    def has_falling(self, results: List[TrendResult]) -> bool:
        return any(r.direction == TrendDirection.FALLING for r in results)

    def filter_by_direction(
        self, results: List[TrendResult], direction: TrendDirection
    ) -> List[TrendResult]:
        return [r for r in results if r.direction == direction]
