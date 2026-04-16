"""Text and JSON reporting for spike detection results."""
from __future__ import annotations

import json
from typing import Dict

from pipewatch.spike import SpikeResult


class SpikeReporter:
    def __init__(self, results: Dict[str, SpikeResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def has_spikes(self) -> bool:
        return any(r.is_spike for r in self._results.values())

    def format_text(self) -> str:
        if not self._results:
            return "Spike detection: no results available."

        lines = ["Spike Detection Report", "=" * 22]
        for key, result in sorted(self._results.items()):
            label = "SPIKE" if result.is_spike else "ok"
            lines.append(
                f"  {key}: {label}  "
                f"value={result.current_value:.4f}  "
                f"threshold={result.threshold:.4f}  "
                f"mean={result.mean:.4f}  "
                f"std={result.std_dev:.4f}"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        payload = {
            "spike_detection": {
                key: result.to_dict()
                for key, result in sorted(self._results.items())
            }
        }
        return json.dumps(payload, indent=2)
