"""Human-readable and JSON reporting for forecast results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.forecast import ForecastResult


class ForecastReporter:
    def __init__(self, results: List[ForecastResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def format_text(self) -> str:
        if not self._results:
            return "No forecast results available."
        lines = ["Forecast Report", "=" * 40]
        for r in self._results:
            lines.append(
                f"  {r.metric_key}: predicted={r.predicted_value:.4f} "
                f"(+{r.steps_ahead} step(s), confidence={r.confidence.value}, "
                f"n={r.sample_count})"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {"forecasts": [r.to_dict() for r in self._results]},
            indent=2,
        )

    def low_confidence_keys(self) -> List[str]:
        from pipewatch.forecast import ForecastConfidence
        return [
            r.metric_key
            for r in self._results
            if r.confidence == ForecastConfidence.LOW
        ]
