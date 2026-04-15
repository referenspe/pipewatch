"""Reporter for stagger plans — human-readable and JSON output."""
from __future__ import annotations

from typing import Optional
import json

from pipewatch.stagger import StaggerPlan


class StaggerReporter:
    def __init__(self, plan: StaggerPlan) -> None:
        self._plan = plan

    @property
    def has_targets(self) -> bool:
        return bool(self._plan.offsets)

    def format_text(self) -> str:
        if not self.has_targets:
            return "Stagger plan: no targets scheduled."

        lines = ["Stagger plan:", ""]
        for name, offset in sorted(self._plan.offsets.items(), key=lambda kv: kv[1]):
            lines.append(f"  {name:<40}  +{offset:6.2f}s")
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(self._plan.to_dict(), indent=2)

    def ordered_targets(self) -> list:
        """Return target names sorted by their assigned offset."""
        return [
            name
            for name, _ in sorted(
                self._plan.offsets.items(), key=lambda kv: kv[1]
            )
        ]

    def max_offset(self) -> Optional[float]:
        if not self._plan.offsets:
            return None
        return max(self._plan.offsets.values())

    def min_offset(self) -> Optional[float]:
        if not self._plan.offsets:
            return None
        return min(self._plan.offsets.values())
