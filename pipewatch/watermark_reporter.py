"""Text and JSON reporting for watermark results."""
from __future__ import annotations

from typing import Dict
import json

from pipewatch.watermark import WatermarkResult


class WatermarkReporter:
    def __init__(self, results: Dict[str, WatermarkResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def format_text(self) -> str:
        if not self._results:
            return "No watermark data available."
        lines = ["Watermark Report", "-" * 32]
        for key, r in self._results.items():
            reset_tag = " [RESET]" if r.reset else ""
            low_str = f"  low={r.low:.4g}" if r.low is not None else ""
            lines.append(
                f"{key}: current={r.current:.4g}  high={r.high:.4g}{low_str}{reset_tag}"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {key: r.to_dict() for key, r in self._results.items()}, indent=2
        )
