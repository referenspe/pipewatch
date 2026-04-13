"""Reporter for tag-filter activity — shows which targets were kept/dropped."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Sequence


@dataclass
class TagFilterSummary:
    """Holds the outcome of a single filter pass."""

    kept: List[str] = field(default_factory=list)    # names of items that passed
    dropped: List[str] = field(default_factory=list)  # names of items that were removed

    @property
    def total(self) -> int:
        return len(self.kept) + len(self.dropped)

    @property
    def acceptance_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return len(self.kept) / self.total

    def to_dict(self) -> Dict:
        return {
            "kept": self.kept,
            "dropped": self.dropped,
            "total": self.total,
            "acceptance_rate": round(self.acceptance_rate, 4),
        }


class TagFilterReporter:
    """Formats a TagFilterSummary as text or JSON."""

    def __init__(self, summary: TagFilterSummary) -> None:
        self._summary = summary

    @property
    def has_drops(self) -> bool:
        return bool(self._summary.dropped)

    def format_text(self) -> str:
        s = self._summary
        if s.total == 0:
            return "Tag filter: no items evaluated."

        lines: List[str] = [
            f"Tag filter summary  "
            f"({len(s.kept)}/{s.total} passed, "
            f"{s.acceptance_rate * 100:.1f}% acceptance)",
        ]
        if s.kept:
            lines.append("  Kept    : " + ", ".join(s.kept))
        if s.dropped:
            lines.append("  Dropped : " + ", ".join(s.dropped))
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(self._summary.to_dict(), indent=2)
