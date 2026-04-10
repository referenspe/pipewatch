"""Alert channel definitions and notification dispatch for pipewatch."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pipewatch.metrics import MetricStatus, PipelineMetric

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    """Represents a single alert triggered by a metric evaluation."""

    metric_name: str
    status: MetricStatus
    value: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"[{ts}] {self.status.value.upper()} | {self.metric_name}={self.value} — {self.message}"


class AlertChannel:
    """Base class for alert output channels."""

    name: str = "base"

    def send(self, event: AlertEvent) -> None:  # pragma: no cover
        raise NotImplementedError


class LoggingChannel(AlertChannel):
    """Writes alerts to the Python logging system."""

    name = "logging"

    def __init__(self, level_map: Optional[dict] = None) -> None:
        self._level_map = level_map or {
            MetricStatus.WARNING: logging.WARNING,
            MetricStatus.CRITICAL: logging.CRITICAL,
        }

    def send(self, event: AlertEvent) -> None:
        level = self._level_map.get(event.status, logging.INFO)
        logger.log(level, str(event))


class AlertDispatcher:
    """Evaluates a metric and dispatches alerts to registered channels."""

    def __init__(self, channels: Optional[List[AlertChannel]] = None) -> None:
        self._channels: List[AlertChannel] = channels or []

    def add_channel(self, channel: AlertChannel) -> None:
        self._channels.append(channel)

    def dispatch(self, metric: PipelineMetric) -> Optional[AlertEvent]:
        """Send an alert if the metric is not OK. Returns the event or None."""
        if metric.status == MetricStatus.OK:
            return None

        event = AlertEvent(
            metric_name=metric.name,
            status=metric.status,
            value=metric.value,
            message=(
                f"Metric '{metric.name}' is {metric.status.value} "
                f"(value={metric.value})"
            ),
        )
        for channel in self._channels:
            try:
                channel.send(event)
            except Exception as exc:  # noqa: BLE001
                logger.error("Channel %s failed: %s", channel.name, exc)

        return event
