"""Stagger: spread pipeline check intervals to avoid thundering-herd."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import math


@dataclass
class StaggerConfig:
    """Configuration for staggered scheduling."""
    spread_seconds: float = 60.0          # total window to spread checks across
    jitter_fraction: float = 0.1          # random jitter as fraction of slot size
    min_offset_seconds: float = 0.0       # minimum offset applied to any target

    def __post_init__(self) -> None:
        if self.spread_seconds <= 0:
            raise ValueError("spread_seconds must be positive")
        if not (0.0 <= self.jitter_fraction <= 1.0):
            raise ValueError("jitter_fraction must be between 0 and 1")
        if self.min_offset_seconds < 0:
            raise ValueError("min_offset_seconds must be >= 0")

    @classmethod
    def from_dict(cls, data: dict) -> "StaggerConfig":
        return cls(
            spread_seconds=float(data.get("spread_seconds", 60.0)),
            jitter_fraction=float(data.get("jitter_fraction", 0.1)),
            min_offset_seconds=float(data.get("min_offset_seconds", 0.0)),
        )

    def to_dict(self) -> dict:
        return {
            "spread_seconds": self.spread_seconds,
            "jitter_fraction": self.jitter_fraction,
            "min_offset_seconds": self.min_offset_seconds,
        }


@dataclass
class StaggerPlan:
    """Computed stagger offsets for a set of targets."""
    offsets: Dict[str, float] = field(default_factory=dict)  # target_name -> offset_seconds

    def offset_for(self, name: str) -> Optional[float]:
        return self.offsets.get(name)

    def to_dict(self) -> dict:
        return {"offsets": dict(self.offsets)}


class Stagger:
    """Assigns staggered start offsets to a list of target names."""

    def __init__(self, config: Optional[StaggerConfig] = None) -> None:
        self.config = config or StaggerConfig()

    def plan(self, target_names: List[str], seed: Optional[int] = None) -> StaggerPlan:
        """Return a StaggerPlan distributing targets evenly across the spread window."""
        import random
        rng = random.Random(seed)

        n = len(target_names)
        if n == 0:
            return StaggerPlan()

        slot = self.config.spread_seconds / n
        jitter_max = slot * self.config.jitter_fraction
        offsets: Dict[str, float] = {}

        for i, name in enumerate(target_names):
            base = self.config.min_offset_seconds + i * slot
            jitter = rng.uniform(-jitter_max / 2, jitter_max / 2)
            offsets[name] = max(self.config.min_offset_seconds, base + jitter)

        return StaggerPlan(offsets=offsets)

    def slot_size(self, n: int) -> float:
        """Return the slot size in seconds for *n* targets."""
        if n <= 0:
            return self.config.spread_seconds
        return self.config.spread_seconds / n
