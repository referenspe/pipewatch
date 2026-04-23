"""Marker module: tag pipeline events with named markers and track their occurrence counts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MarkerConfig:
    max_markers: int = 100
    track_counts: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "MarkerConfig":
        return cls(
            max_markers=data.get("max_markers", 100),
            track_counts=data.get("track_counts", True),
        )

    def to_dict(self) -> dict:
        return {
            "max_markers": self.max_markers,
            "track_counts": self.track_counts,
        }


@dataclass
class MarkerEvent:
    key: str
    label: str
    count: int = 0

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "count": self.count}


@dataclass
class MarkerResult:
    events: List[MarkerEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"events": [e.to_dict() for e in self.events]}


@dataclass
class Marker:
    config: MarkerConfig = field(default_factory=MarkerConfig)
    _store: Dict[str, MarkerEvent] = field(default_factory=dict, init=False, repr=False)

    def mark(self, key: str, label: str) -> Optional[MarkerEvent]:
        """Record a marker occurrence. Returns None if max_markers exceeded."""
        if key not in self._store:
            if len(self._store) >= self.config.max_markers:
                return None
            self._store[key] = MarkerEvent(key=key, label=label)
        event = self._store[key]
        if self.config.track_counts:
            event.count += 1
        return event

    def get(self, key: str) -> Optional[MarkerEvent]:
        return self._store.get(key)

    def reset(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def report(self) -> MarkerResult:
        return MarkerResult(events=list(self._store.values()))
