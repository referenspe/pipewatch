"""Human-readable and JSON reporting for partition analysis results."""
from __future__ import annotations

import json
from typing import List

from pipewatch.partition import PartitionResult


class PartitionReporter:
    def __init__(self, title: str = "Partition Report") -> None:
        self._title = title

    def has_critical(self, result: PartitionResult) -> bool:
        from pipewatch.metrics import MetricStatus
        return any(
            g.worst_status == MetricStatus.CRITICAL
            for g in result.groups.values()
        )

    def has_warnings(self, result: PartitionResult) -> bool:
        from pipewatch.metrics import MetricStatus
        return any(
            g.worst_status == MetricStatus.WARNING
            for g in result.groups.values()
        )

    def format_text(self, result: PartitionResult) -> str:
        if not result.groups:
            return f"{self._title}\n  (no partitions)"

        lines: List[str] = [f"{self._title}"]
        if result.truncated:
            lines.append("  [!] result truncated — max_partitions reached")

        for key, group in sorted(result.groups.items()):
            avg = (
                f"{group.average_value:.4f}"
                if group.average_value is not None
                else "n/a"
            )
            lines.append(
                f"  [{group.worst_status.value.upper():8s}] "
                f"{key}  count={group.count}  avg={avg}"
            )

        return "\n".join(lines)

    def format_json(self, result: PartitionResult) -> str:
        return json.dumps(
            {"title": self._title, "result": result.to_dict()},
            indent=2,
        )
