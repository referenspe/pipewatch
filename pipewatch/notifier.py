"""Notifier module: aggregates alert channels and dispatches AlertEvents."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.alerts import AlertChannel, AlertEvent
from pipewatch.metrics import MetricStatus
from pipewatch.watcher import WatchResult

logger = logging.getLogger(__name__)


@dataclass
class NotifierConfig:
    """Configuration controlling when notifications are sent."""

    min_status: MetricStatus = MetricStatus.WARNING
    """Only dispatch events at or above this severity."""

    deduplicate: bool = True
    """Skip re-alerting if the same metric fires the same status consecutively."""


class Notifier:
    """Dispatches :class:`AlertEvent` objects to registered channels.

    Parameters
    ----------
    channels:
        One or more :class:`~pipewatch.alerts.AlertChannel` implementations.
    config:
        Optional :class:`NotifierConfig`; defaults are used when omitted.
    """

    def __init__(
        self,
        channels: Optional[List[AlertChannel]] = None,
        config: Optional[NotifierConfig] = None,
    ) -> None:
        self._channels: List[AlertChannel] = list(channels or [])
        self._config = config or NotifierConfig()
        # Maps metric name -> last alerted status for deduplication
        self._last_status: dict[str, MetricStatus] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_channel(self, channel: AlertChannel) -> None:
        """Register an additional alert channel at runtime."""
        self._channels.append(channel)

    def notify_from_result(self, result: WatchResult) -> int:
        """Evaluate a :class:`~pipewatch.watcher.WatchResult` and fire alerts.

        Returns the number of events dispatched.
        """
        dispatched = 0
        for metric in result.metrics:
            if metric.status < self._config.min_status:
                continue
            if self._config.deduplicate:
                if self._last_status.get(metric.name) == metric.status:
                    logger.debug(
                        "Skipping duplicate alert for %s (%s)",
                        metric.name,
                        metric.status,
                    )
                    continue
            event = AlertEvent(metric=metric, target_name=result.target_name)
            self._dispatch(event)
            self._last_status[metric.name] = metric.status
            dispatched += 1
        return dispatched

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _dispatch(self, event: AlertEvent) -> None:
        for channel in self._channels:
            try:
                channel.send(event)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Channel %s failed to send event for %s",
                    type(channel).__name__,
                    event.metric.name,
                )
