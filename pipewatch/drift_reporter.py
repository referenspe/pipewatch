"""Human-readable and JSON reporting for drift detection results."""
from __future__ import annotations

import json
from typing import Dict

from pipewatch.drift import DriftResult
from pipewatch.metrics import MetricStatus

_STATUS_LABEL: Dict[MetricStatus, str] = {
    MetricStatus.OK: "OK",
    MetricStatus.WARNING: "WARN",
    MetricStatus.CRITICAL: "CRIT",
}


class DriftReporter:
    """Format drift results for display or export."""

    def __init__(self, results: Dict[str, DriftResult]) -> None:
        self._results = results

    @property
    def has_results(self) -> bool:
        return bool(self._results)

    def has_drift(self) -> bool:
        return any(
            r.status != MetricStatus.OK for r in self._results.values()
        )

    def has_critical(self) -> bool:
        return any(
            r.status == MetricStatus.CRITICAL for r in self._results.values()
        )

    def format_text(self) -> str:
        if not self._results:
            return "Drift: no results available."
        lines = ["=== Drift Report ==="]
        for key, result in sorted(self._results.items()):
            label = _STATUS_LABEL[result.status]
            shift_pct = result.relative_shift * 100
            direction = "+" if shift_pct >= 0 else ""
            lines.append(
                f"  [{label}] {key}: baseline={result.baseline_mean:.4f} "
                f"current={result.current_mean:.4f} "
                f"shift={direction}{shift_pct:.2f}%"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {key: result.to_dict() for key, result in self._results.items()},
            indent=2,
        )
