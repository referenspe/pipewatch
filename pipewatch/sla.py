"""SLA (Service Level Agreement) tracking for pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class SLAConfig:
    """Configuration for an SLA policy."""
    target_availability: float = 99.9  # percent
    max_breach_minutes: int = 5
    window_hours: int = 24

    @staticmethod
    def from_dict(data: dict) -> "SLAConfig":
        return SLAConfig(
            target_availability=data.get("target_availability", 99.9),
            max_breach_minutes=data.get("max_breach_minutes", 5),
            window_hours=data.get("window_hours", 24),
        )

    def to_dict(self) -> dict:
        return {
            "target_availability": self.target_availability,
            "max_breach_minutes": self.max_breach_minutes,
            "window_hours": self.window_hours,
        }


@dataclass
class SLABreachEvent:
    """Records a single SLA breach window."""
    metric_key: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    @property
    def duration_minutes(self) -> float:
        end = self.ended_at or datetime.utcnow()
        return (end - self.started_at).total_seconds() / 60

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": round(self.duration_minutes, 2),
        }


@dataclass
class SLAResult:
    """Outcome of evaluating SLA compliance for a metric."""
    metric_key: str
    availability_pct: float
    breaches: List[SLABreachEvent] = field(default_factory=list)
    compliant: bool = True

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "availability_pct": round(self.availability_pct, 4),
            "compliant": self.compliant,
            "breach_count": len(self.breaches),
            "breaches": [b.to_dict() for b in self.breaches],
        }


class SLATracker:
    """Tracks SLA compliance across multiple metric keys."""

    def __init__(self, config: SLAConfig) -> None:
        self._config = config
        self._breaches: Dict[str, List[SLABreachEvent]] = {}

    def record_breach(self, metric_key: str, started_at: datetime,
                      ended_at: Optional[datetime] = None) -> None:
        self._breaches.setdefault(metric_key, []).append(
            SLABreachEvent(metric_key=metric_key, started_at=started_at, ended_at=ended_at)
        )

    def evaluate(self, metric_key: str, now: Optional[datetime] = None) -> SLAResult:
        now = now or datetime.utcnow()
        window_start = now - timedelta(hours=self._config.window_hours)
        window_minutes = self._config.window_hours * 60

        relevant = [
            b for b in self._breaches.get(metric_key, [])
            if (b.ended_at or now) >= window_start
        ]

        breached_minutes = sum(
            min(b.duration_minutes, window_minutes) for b in relevant
        )
        availability = max(0.0, (1 - breached_minutes / window_minutes) * 100)
        compliant = availability >= self._config.target_availability

        return SLAResult(
            metric_key=metric_key,
            availability_pct=availability,
            breaches=relevant,
            compliant=compliant,
        )

    def evaluate_all(self, now: Optional[datetime] = None) -> List[SLAResult]:
        return [self.evaluate(key, now=now) for key in self._breaches]
