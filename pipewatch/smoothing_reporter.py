"""Reporter for smoothed metric series."""
from __future__ import annotations

import json
from typing import Optional

from pipewatch.smoothing import SmoothingResult


class SmoothingReporter:
    def __init__(self, result: SmoothingResult) -> None:
        self._result = result

    def has_results(self) -> bool:
        return bool(self._result.series)

    def format_text(self) -> str:
        if not self.has_results():
            return "smoothing: no series processed"
        lines = ["=== Smoothed Metrics ==="]
        for s in self._result.series:
            delta = s.latest_smoothed - s.latest_raw
            direction = "▲" if delta >= 0 else "▼"
            lines.append(
                f"  {s.key}: raw={s.latest_raw:.4f}  "
                f"ema={s.latest_smoothed:.4f}  "
                f"{direction} {abs(delta):.4f}  "
                f"(n={len(s.values)})"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(self._result.to_dict(), indent=2)

    @property
    def series_count(self) -> int:
        return len(self._result.series)
