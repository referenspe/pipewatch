"""Formats sampler statistics for human-readable and JSON output."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SamplerStats:
    """Snapshot of sampler activity for a single metric key."""
    key: str
    allowed: int = 0
    denied: int = 0

    @property
    def total(self) -> int:
        return self.allowed + self.denied

    @property
    def acceptance_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.allowed / self.total

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "allowed": self.allowed,
            "denied": self.denied,
            "total": self.total,
            "acceptance_rate": round(self.acceptance_rate, 4),
        }


class SamplerReporter:
    """Accumulates sampler decisions and produces summary reports."""

    def __init__(self) -> None:
        self._stats: Dict[str, SamplerStats] = {}

    def record(self, key: str, *, allowed: bool) -> None:
        """Record a single sampler decision for *key*."""
        if key not in self._stats:
            self._stats[key] = SamplerStats(key=key)
        if allowed:
            self._stats[key].allowed += 1
        else:
            self._stats[key].denied += 1

    def all_stats(self) -> List[SamplerStats]:
        return sorted(self._stats.values(), key=lambda s: s.key)

    def has_denials(self) -> bool:
        return any(s.denied > 0 for s in self._stats.values())

    def format_text(self) -> str:
        if not self._stats:
            return "No sampler activity recorded."
        lines = ["Sampler report:", ""]
        for s in self.all_stats():
            pct = f"{s.acceptance_rate * 100:.1f}%"
            lines.append(
                f"  {s.key}: {s.allowed}/{s.total} allowed ({pct})"
            )
        return "\n".join(lines)

    def format_json(self) -> str:
        return json.dumps(
            {"sampler_stats": [s.to_dict() for s in self.all_stats()]},
            indent=2,
        )
