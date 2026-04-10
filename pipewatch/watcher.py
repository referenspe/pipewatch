"""Pipeline watcher: periodically samples metrics and triggers alerts."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from pipewatch.alerts import AlertDispatcher, AlertEvent
from pipewatch.metrics import ThresholdConfig, evaluate

logger = logging.getLogger(__name__)


@dataclass
class WatchTarget:
    """A single named metric to watch with its sampler and threshold config."""

    name: str
    sampler: Callable[[], float]
    config: ThresholdConfig


@dataclass
class WatchResult:
    """Aggregated results from one poll cycle."""

    events: List[AlertEvent] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def has_alerts(self) -> bool:
        return bool(self.events)


class PipelineWatcher:
    """Polls registered metrics and dispatches alerts via an AlertDispatcher."""

    def __init__(self, dispatcher: Optional[AlertDispatcher] = None) -> None:
        self._targets: List[WatchTarget] = []
        self._dispatcher = dispatcher or AlertDispatcher()

    def register(self, target: WatchTarget) -> None:
        """Register a metric target for polling."""
        self._targets.append(target)

    def poll(self) -> WatchResult:
        """Sample all targets once and return a WatchResult."""
        result = WatchResult()
        for target in self._targets:
            try:
                value = target.sampler()
                metric = evaluate(target.name, value, target.config)
                event = self._dispatcher.dispatch(metric)
                if event is not None:
                    result.events.append(event)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error sampling '%s': %s", target.name, exc)
                result.errors[target.name] = str(exc)
        return result

    def run(self, interval: float = 5.0, max_cycles: Optional[int] = None) -> None:
        """Blocking loop that polls at *interval* seconds.

        Args:
            interval: Seconds between poll cycles.
            max_cycles: Stop after this many cycles (useful for testing / CI).
        """
        cycle = 0
        logger.info("PipelineWatcher starting (interval=%.1fs)", interval)
        while max_cycles is None or cycle < max_cycles:
            result = self.poll()
            if result.errors:
                logger.warning("Sampler errors: %s", result.errors)
            cycle += 1
            if max_cycles is None or cycle < max_cycles:
                time.sleep(interval)
        logger.info("PipelineWatcher finished after %d cycle(s)", cycle)
