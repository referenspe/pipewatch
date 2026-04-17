"""Pause/resume control for pipeline watchers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class PauseConfig:
    max_pause_seconds: int = 3600
    auto_resume: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "PauseConfig":
        return cls(
            max_pause_seconds=data.get("max_pause_seconds", 3600),
            auto_resume=data.get("auto_resume", True),
        )

    def to_dict(self) -> dict:
        return {
            "max_pause_seconds": self.max_pause_seconds,
            "auto_resume": self.auto_resume,
        }


@dataclass
class PauseResult:
    key: str
    paused: bool
    paused_at: Optional[datetime]
    resumed_at: Optional[datetime]
    auto_resumed: bool = False

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "paused": self.paused,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "resumed_at": self.resumed_at.isoformat() if self.resumed_at else None,
            "auto_resumed": self.auto_resumed,
        }


@dataclass
class PauseController:
    config: PauseConfig = field(default_factory=PauseConfig)
    _state: Dict[str, datetime] = field(default_factory=dict, init=False)

    def pause(self, key: str, now: Optional[datetime] = None) -> PauseResult:
        ts = now or datetime.now(timezone.utc)
        self._state[key] = ts
        return PauseResult(key=key, paused=True, paused_at=ts, resumed_at=None)

    def resume(self, key: str, now: Optional[datetime] = None, auto: bool = False) -> PauseResult:
        ts = now or datetime.now(timezone.utc)
        paused_at = self._state.pop(key, None)
        return PauseResult(key=key, paused=False, paused_at=paused_at, resumed_at=ts, auto_resumed=auto)

    def check(self, key: str, now: Optional[datetime] = None) -> PauseResult:
        ts = now or datetime.now(timezone.utc)
        paused_at = self._state.get(key)
        if paused_at is None:
            return PauseResult(key=key, paused=False, paused_at=None, resumed_at=None)
        elapsed = (ts - paused_at).total_seconds()
        if self.config.auto_resume and elapsed >= self.config.max_pause_seconds:
            return self.resume(key, now=ts, auto=True)
        return PauseResult(key=key, paused=True, paused_at=paused_at, resumed_at=None)

    def is_paused(self, key: str, now: Optional[datetime] = None) -> bool:
        return self.check(key, now=now).paused

    def paused_keys(self) -> list:
        return list(self._state.keys())
