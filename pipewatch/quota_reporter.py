"""Human-readable and JSON reporting for QuotaEnforcer results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.quota import QuotaResult


class QuotaReporter:
    def __init__(self, results: List[QuotaResult]) -> None:
        self._results = results

    def has_violations(self) -> bool:
        return any(not r.allowed for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Quota: no results recorded."
        lines = ["Quota Report", "-" * 40]
        for r in self._results:
            status = "ALLOWED" if r.allowed else "BLOCKED"
            pct = int(r.current_count / r.limit * 100) if r.limit else 0
            lines.append(
                f"  [{status}] {r.key}: {r.current_count}/{r.limit} "
                f"({pct}%) in {r.window_seconds}s window"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {
                "quota_violations": self.has_violations(),
                "results": [r.to_dict() for r in self._results],
            },
            indent=2,
        )
