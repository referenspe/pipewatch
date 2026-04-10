"""Core metrics collection and representation for pipeline health monitoring."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MetricStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class PipelineMetric:
    """Represents a single health metric snapshot for a pipeline."""

    pipeline_name: str
    metric_name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: MetricStatus = MetricStatus.UNKNOWN
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pipeline": self.pipeline_name,
            "metric": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "tags": self.tags,
        }


@dataclass
class ThresholdConfig:
    """Warning and critical thresholds for a metric."""

    warning: Optional[float] = None
    critical: Optional[float] = None
    comparison: str = "gt"  # 'gt' or 'lt'

    def evaluate(self, value: float) -> MetricStatus:
        """Determine metric status based on thresholds."""
        def exceeds(threshold: float) -> bool:
            return value > threshold if self.comparison == "gt" else value < threshold

        if self.critical is not None and exceeds(self.critical):
            return MetricStatus.CRITICAL
        if self.warning is not None and exceeds(self.warning):
            return MetricStatus.WARNING
        return MetricStatus.OK


class MetricsCollector:
    """Collects and evaluates pipeline metrics against configured thresholds."""

    def __init__(self):
        self._thresholds: dict[str, ThresholdConfig] = {}
        self._history: list[PipelineMetric] = []

    def register_threshold(self, metric_name: str, config: ThresholdConfig) -> None:
        """Register a threshold configuration for a given metric name."""
        self._thresholds[metric_name] = config

    def record(self, pipeline_name: str, metric_name: str, value: float, unit: str = "", tags: dict = None) -> PipelineMetric:
        """Record a metric value and evaluate its status."""
        threshold = self._thresholds.get(metric_name)
        status = threshold.evaluate(value) if threshold else MetricStatus.UNKNOWN

        metric = PipelineMetric(
            pipeline_name=pipeline_name,
            metric_name=metric_name,
            value=value,
            unit=unit,
            status=status,
            tags=tags or {},
        )
        self._history.append(metric)
        return metric

    def latest(self, limit: int = 50) -> list[PipelineMetric]:
        """Return the most recent metrics."""
        return self._history[-limit:]

    def clear(self) -> None:
        """Clear all recorded metrics."""
        self._history.clear()
