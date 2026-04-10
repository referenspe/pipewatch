"""Scheduler for periodically running pipeline watchers and dispatching alerts."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from pipewatch.watcher import PipelineWatcher, WatchResult
from pipewatch.alerts import AlertChannel
from pipewatch.reporter import Report, format_report

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """Configuration for the polling scheduler."""

    interval_seconds: float = 60.0
    max_iterations: Optional[int] = None  # None means run indefinitely


@dataclass
class Scheduler:
    """Runs a PipelineWatcher on a fixed interval and dispatches alerts."""

    watcher: PipelineWatcher
    channels: List[AlertChannel]
    config: SchedulerConfig = field(default_factory=SchedulerConfig)
    _iteration_count: int = field(default=0, init=False, repr=False)

    def run_once(self) -> Report:
        """Execute a single watch cycle and send alerts for any triggered targets."""
        results: List[WatchResult] = []
        for target in self.watcher.targets:
            result = self.watcher.run(target)
            results.append(result)
            if result.has_alerts():
                for channel in self.channels:
                    for event in result.alert_events:
                        try:
                            channel.send(event)
                        except Exception as exc:  # noqa: BLE001
                            logger.error("Failed to send alert via %s: %s", channel, exc)

        report = Report(results=results)
        logger.debug("Scheduler cycle complete:\n%s", format_report(report))
        return report

    def start(self, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        """Start the polling loop. Blocks until max_iterations is reached."""
        logger.info(
            "Scheduler starting — interval=%.1fs max_iterations=%s",
            self.config.interval_seconds,
            self.config.max_iterations,
        )
        while True:
            self._iteration_count += 1
            logger.debug("Scheduler iteration %d", self._iteration_count)
            self.run_once()

            if (
                self.config.max_iterations is not None
                and self._iteration_count >= self.config.max_iterations
            ):
                logger.info("Reached max_iterations (%d), stopping.", self.config.max_iterations)
                break

            sleep_fn(self.config.interval_seconds)
