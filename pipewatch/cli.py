"""Entry-point CLI for pipewatch using the Scheduler."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from pipewatch.alerts import LoggingChannel
from pipewatch.scheduler import Scheduler, SchedulerConfig
from pipewatch.watcher import PipelineWatcher

logger = logging.getLogger(__name__)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch",
        description="Monitor and alert on data pipeline health metrics in real time.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Polling interval in seconds (default: 60).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N iterations (default: run forever).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def run(argv: List[str] | None = None) -> int:
    """Parse arguments, build scheduler, and start the watch loop.

    Returns an exit code (0 = success).
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    _configure_logging(args.log_level)
    logger.info("pipewatch starting up")

    watcher = PipelineWatcher(targets=[])
    config = SchedulerConfig(
        interval_seconds=args.interval,
        max_iterations=args.iterations,
    )
    channels = [LoggingChannel()]

    scheduler = Scheduler(watcher=watcher, channels=channels, config=config)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down.")

    return 0


def main() -> None:  # pragma: no cover
    sys.exit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
