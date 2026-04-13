"""Checkpoint tracking for pipeline stages — records last-seen positions
so that a watcher can detect stalls or regressions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CheckpointConfig:
    stall_after: float = 300.0   # seconds before a checkpoint is considered stalled
    max_history: int = 50

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointConfig":
        return cls(
            stall_after=float(data.get("stall_after", 300.0)),
            max_history=int(data.get("max_history", 50)),
        )

    def to_dict(self) -> dict:
        return {"stall_after": self.stall_after, "max_history": self.max_history}


@dataclass
class CheckpointEntry:
    stage: str
    position: float          # monotonically increasing value (offset, row count, etc.)
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "position": self.position,
            "recorded_at": self.recorded_at,
        }


@dataclass
class CheckpointResult:
    stage: str
    stalled: bool
    regressed: bool
    last_position: Optional[float]
    current_position: float
    seconds_since_update: float

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "stalled": self.stalled,
            "regressed": self.regressed,
            "last_position": self.last_position,
            "current_position": self.current_position,
            "seconds_since_update": round(self.seconds_since_update, 3),
        }


class CheckpointTracker:
    """Records pipeline stage positions and detects stalls / regressions."""

    def __init__(self, config: Optional[CheckpointConfig] = None) -> None:
        self._config = config or CheckpointConfig()
        self._history: Dict[str, List[CheckpointEntry]] = {}

    def record(self, stage: str, position: float, now: Optional[float] = None) -> None:
        ts = now if now is not None else time.time()
        entry = CheckpointEntry(stage=stage, position=position, recorded_at=ts)
        bucket = self._history.setdefault(stage, [])
        bucket.append(entry)
        if len(bucket) > self._config.max_history:
            bucket.pop(0)

    def evaluate(self, stage: str, now: Optional[float] = None) -> Optional[CheckpointResult]:
        bucket = self._history.get(stage)
        if not bucket:
            return None
        ts = now if now is not None else time.time()
        latest = bucket[-1]
        previous = bucket[-2] if len(bucket) >= 2 else None
        seconds_since = ts - latest.recorded_at
        stalled = seconds_since >= self._config.stall_after
        regressed = (
            previous is not None and latest.position < previous.position
        )
        return CheckpointResult(
            stage=stage,
            stalled=stalled,
            regressed=regressed,
            last_position=previous.position if previous else None,
            current_position=latest.position,
            seconds_since_update=seconds_since,
        )

    def stages(self) -> List[str]:
        return list(self._history.keys())
