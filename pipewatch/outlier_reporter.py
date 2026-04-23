"""Text and JSON reporting for outlier detection results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.metrics import MetricStatus
from pipewatch.outlier import OutlierResult


class OutlierReporter:
    def __init__(self, results: List[OutlierResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return len(self._results) > 0

    def has_outliers(self) -> bool:
        return any(r.status != MetricStatus.OK for r in self._results)

    def has_critical(self) -> bool:
        return any(r.status == MetricStatus.CRITICAL for r in self._results)

    def outlier_results(self) -> List[OutlierResult]:
        return [r for r in self._results if r.status != MetricStatus.OK]

    def format_text(self) -> str:
        if not self._results:
            return "Outlier detection: no results."
        lines = ["Outlier Detection Results:", ""]
        for r in self._results:
            label = r.status.value.upper()
            lines.append(
                f"  [{label}] {r.metric_key}: value={r.value:.4f} "
                f"fence=[{r.lower_fence:.4f}, {r.upper_fence:.4f}] "
                f"IQR={r.iqr:.4f}"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)
