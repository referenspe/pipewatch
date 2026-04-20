"""Reporter for eviction results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.eviction import EvictionResult


class EvictionReporter:
    def __init__(self, results: List[EvictionResult]) -> None:
        self._results = results

    @property
    def has_results(self) -> bool:
        return bool(self._results)

    @property
    def total_evicted(self) -> int:
        return len(self._results)

    def by_reason(self, reason: str) -> List[EvictionResult]:
        return [r for r in self._results if r.reason == reason]

    def format_text(self) -> str:
        if not self._results:
            return "Eviction: no keys evicted."

        lines = [f"Eviction: {self.total_evicted} key(s) removed."]
        for r in self._results:
            lines.append(
                f"  [{r.reason.upper()}] {r.key}  age={r.age_seconds:.1f}s  ok_streak={r.ok_streak}"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {
                "total_evicted": self.total_evicted,
                "evictions": [r.to_dict() for r in self._results],
            },
            indent=2,
        )
