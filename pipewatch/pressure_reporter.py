"""Reporter for pressure monitor results."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict

from pipewatch.metrics import MetricStatus
from pipewatch.pressure import PressureResult


@dataclass
class PressureReporter:
    results: Dict[str, PressureResult] = field(default_factory=dict)

    @property
    def has_results(self) -> bool:
        return bool(self.results)

    @property
    def has_warnings(self) -> bool:
        return any(
            r.status == MetricStatus.WARNING for r in self.results.values()
        )

    @property
    def has_critical(self) -> bool:
        return any(
            r.status == MetricStatus.CRITICAL for r in self.results.values()
        )

    def format_text(self) -> str:
        if not self.results:
            return "[pressure] no results"
        lines = ["[pressure]"]
        for key, result in sorted(self.results.items()):
            label = result.status.value.upper()
            lines.append(
                f"  {key}: {label} — {result.message}"
                f" (samples={result.sample_count})"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {key: r.to_dict() for key, r in self.results.items()},
            indent=2,
        )
