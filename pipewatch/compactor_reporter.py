"""Human-readable and JSON reporting for Compactor results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.compactor import CompactResult


class CompactorReporter:
    def __init__(self, results: List[CompactResult]) -> None:
        self._results = results

    def has_results(self) -> bool:
        return bool(self._results)

    def total_removed(self) -> int:
        return sum(r.snapshots_removed for r in self._results)

    def total_buckets(self) -> int:
        return sum(r.buckets_created for r in self._results)

    def format_text(self) -> str:
        if not self._results:
            return "Compactor: no compaction performed."
        lines = ["Compactor summary:"]
        for r in self._results:
            lines.append(
                f"  [{r.key}] removed={r.snapshots_removed} "
                f"new_buckets={r.buckets_created}"
            )
        lines.append(
            f"  Total snapshots removed: {self.total_removed()}, "
            f"buckets created: {self.total_buckets()}"
        )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {
                "compactor": {
                    "total_removed": self.total_removed(),
                    "total_buckets": self.total_buckets(),
                    "results": [r.to_dict() for r in self._results],
                }
            },
            indent=2,
        )
