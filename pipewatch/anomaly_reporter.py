"""Formats anomaly detection results for CLI output."""

from __future__ import annotations

import json
from typing import List

from pipewatch.anomaly import AnomalyLevel, AnomalyResult

_LEVEL_LABELS = {
    AnomalyLevel.NONE: "OK",
    AnomalyLevel.MILD: "MILD ANOMALY",
    AnomalyLevel.SEVERE: "SEVERE ANOMALY",
}


class AnomalyReporter:
    """Renders a list of AnomalyResult objects as text or JSON."""

    def __init__(self, results: List[AnomalyResult]) -> None:
        self._results = results

    def format_text(self) -> str:
        if not self._results:
            return "No anomaly data available."
        lines = ["Anomaly Report", "-" * 40]
        for r in self._results:
            label = _LEVEL_LABELS[r.level]
            lines.append(
                f"  {r.metric_key}: {label} "
                f"(value={r.value:.4f}, z={r.z_score:.2f}, "
                f"mean={r.mean:.4f}, std={r.std_dev:.4f})"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps([r.to_dict() for r in self._results], indent=2)

    def has_anomalies(self) -> bool:
        return any(r.level != AnomalyLevel.NONE for r in self._results)

    def has_severe(self) -> bool:
        return any(r.level == AnomalyLevel.SEVERE for r in self._results)

    def summary(self) -> str:
        """Return a one-line summary of anomaly counts by level.

        Example output: "3 metrics checked: 1 mild, 1 severe, 1 OK"
        """
        counts = {level: 0 for level in AnomalyLevel}
        for r in self._results:
            counts[r.level] += 1
        total = len(self._results)
        ok = counts[AnomalyLevel.NONE]
        mild = counts[AnomalyLevel.MILD]
        severe = counts[AnomalyLevel.SEVERE]
        return (
            f"{total} metrics checked: "
            f"{severe} severe, {mild} mild, {ok} OK"
        )
