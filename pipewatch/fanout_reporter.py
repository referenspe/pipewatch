"""Reporter for Fanout dispatch results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.fanout import FanoutResult


class FanoutReporter:
    """Formats a collection of FanoutResult objects for display."""

    def __init__(self, results: List[FanoutResult]) -> None:
        self._results = results

    @property
    def has_results(self) -> bool:
        return bool(self._results)

    @property
    def has_failures(self) -> bool:
        return any(r.has_failures for r in self._results)

    @property
    def total_sent(self) -> int:
        return sum(r.total_sent for r in self._results)

    @property
    def total_failed(self) -> int:
        return sum(len(r.failed) for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "fanout: no dispatch results"
        lines = ["=== Fanout Dispatch Report ==="]
        for r in self._results:
            status = "FAIL" if r.has_failures else "OK"
            lines.append(
                f"  [{status}] {r.metric_key}: "
                f"sent={r.total_sent} failed={len(r.failed)}"
            )
            for ch, err in r.failed.items():
                lines.append(f"    ! {ch}: {err}")
        lines.append(
            f"  total sent={self.total_sent} total failed={self.total_failed}"
        )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {
                "fanout_results": [r.to_dict() for r in self._results],
                "total_sent": self.total_sent,
                "total_failed": self.total_failed,
            },
            indent=2,
        )
