"""Replay engine: re-run historical metric snapshots through the evaluation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.metrics import PipelineMetric, ThresholdConfig, evaluate


@dataclass
class ReplayConfig:
    """Configuration for a replay run."""
    max_snapshots: int = 500
    stop_on_critical: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayConfig":
        return cls(
            max_snapshots=int(data.get("max_snapshots", 500)),
            stop_on_critical=bool(data.get("stop_on_critical", False)),
        )

    def to_dict(self) -> dict:
        return {
            "max_snapshots": self.max_snapshots,
            "stop_on_critical": self.stop_on_critical,
        }


@dataclass
class ReplayEvent:
    """A single evaluated snapshot produced during replay."""
    snapshot: MetricSnapshot
    metric: PipelineMetric

    def to_dict(self) -> dict:
        return {
            "timestamp": self.snapshot.timestamp.isoformat(),
            "metric": self.metric.to_dict(),
        }


@dataclass
class ReplayResult:
    """Aggregated outcome of a replay run."""
    key: str
    events: List[ReplayEvent] = field(default_factory=list)
    stopped_early: bool = False

    @property
    def total(self) -> int:
        return len(self.events)

    @property
    def critical_count(self) -> int:
        from pipewatch.metrics import MetricStatus
        return sum(1 for e in self.events if e.metric.status == MetricStatus.CRITICAL)

    @property
    def warning_count(self) -> int:
        from pipewatch.metrics import MetricStatus
        return sum(1 for e in self.events if e.metric.status == MetricStatus.WARNING)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "total": self.total,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "stopped_early": self.stopped_early,
            "events": [e.to_dict() for e in self.events],
        }


class ReplayEngine:
    """Replays stored snapshots through threshold evaluation."""

    def __init__(self, config: Optional[ReplayConfig] = None) -> None:
        self.config = config or ReplayConfig()

    def run(self, key: str, history: MetricHistory, threshold: ThresholdConfig) -> ReplayResult:
        """Evaluate all snapshots for *key* and return a ReplayResult."""
        from pipewatch.metrics import MetricStatus

        snapshots = history.all(key)[: self.config.max_snapshots]
        result = ReplayResult(key=key)

        for snap in snapshots:
            metric = evaluate(key, snap.value, threshold)
            event = ReplayEvent(snapshot=snap, metric=metric)
            result.events.append(event)
            if self.config.stop_on_critical and metric.status == MetricStatus.CRITICAL:
                result.stopped_early = True
                break

        return result
