"""dashboard.py — Terminal dashboard renderer for real-time pipeline health display.

Provides a simple text-based dashboard that can be refreshed in-place using
ANSI escape codes, giving operators a live view of all watched targets.
"""

from __future__ import annotations

import os
import sys
import datetime
from typing import List, Optional

from pipewatch.metrics import MetricStatus
from pipewatch.reporter import Report
from pipewatch.watcher import WatchResult

# ANSI colour codes — fall back gracefully when the terminal doesn't support them
_COLOURS_ENABLED = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

_RESET = "\033[0m" if _COLOURS_ENABLED else ""
_BOLD = "\033[1m" if _COLOURS_ENABLED else ""
_RED = "\033[31m" if _COLOURS_ENABLED else ""
_YELLOW = "\033[33m" if _COLOURS_ENABLED else ""
_GREEN = "\033[32m" if _COLOURS_ENABLED else ""
_CYAN = "\033[36m" if _COLOURS_ENABLED else ""
_DIM = "\033[2m" if _COLOURS_ENABLED else ""

_STATUS_COLOUR = {
    MetricStatus.OK: _GREEN,
    MetricStatus.WARNING: _YELLOW,
    MetricStatus.CRITICAL: _RED,
}

_CLEAR_SCREEN = "\033[2J\033[H" if _COLOURS_ENABLED else ""
_MOVE_HOME = "\033[H" if _COLOURS_ENABLED else ""


def _colour_status(status: MetricStatus, text: str) -> str:
    """Wrap *text* in the ANSI colour that matches *status*."""
    colour = _STATUS_COLOUR.get(status, "")
    return f"{colour}{text}{_RESET}"


def _status_icon(status: MetricStatus) -> str:
    """Return a compact icon representing *status*."""
    return {
        MetricStatus.OK: "✔",
        MetricStatus.WARNING: "⚠",
        MetricStatus.CRITICAL: "✖",
    }.get(status, "?")


class Dashboard:
    """Renders a pipeline health dashboard to an output stream.

    Parameters
    ----------
    stream:
        File-like object to write the dashboard to (defaults to *stdout*).
    clear_on_refresh:
        When *True* the screen is cleared before each render so the output
        appears to update in-place.  Disable for non-interactive/log use.
    """

    def __init__(
        self,
        stream=None,
        *,
        clear_on_refresh: bool = True,
    ) -> None:
        self._stream = stream or sys.stdout
        self._clear_on_refresh = clear_on_refresh
        self._render_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, report: Report, *, timestamp: Optional[datetime.datetime] = None) -> None:
        """Write the dashboard for *report* to the configured stream.

        Parameters
        ----------
        report:
            The :class:`~pipewatch.reporter.Report` produced by the latest
            watcher cycle.
        timestamp:
            The moment the report was generated.  Defaults to *now* (UTC).
        """
        ts = timestamp or datetime.datetime.utcnow()
        lines = self._build_lines(report, ts)

        if self._clear_on_refresh and self._render_count > 0:
            self._stream.write(_MOVE_HOME)
        elif self._clear_on_refresh and self._render_count == 0:
            self._stream.write(_CLEAR_SCREEN)

        self._stream.write("\n".join(lines) + "\n")
        self._stream.flush()
        self._render_count += 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_lines(self, report: Report, ts: datetime.datetime) -> List[str]:
        """Assemble the list of text lines that make up the dashboard."""
        lines: List[str] = []

        overall = report.overall_status()
        overall_text = _colour_status(overall, f"{_status_icon(overall)}  Overall: {overall.value.upper()}")
        header = f"{_BOLD}PipeWatch Dashboard{_RESET}  {overall_text}"
        ts_str = f"{_DIM}Last updated: {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC{_RESET}"

        lines.append(header)
        lines.append(ts_str)
        lines.append(_DIM + "─" * 60 + _RESET)

        if not report.results:
            lines.append(f"{_DIM}No targets monitored yet.{_RESET}")
            return lines

        for result in report.results:
            lines.extend(self._format_result(result))
            lines.append("")  # blank separator between targets

        # Remove trailing blank line
        if lines and lines[-1] == "":
            lines.pop()

        lines.append(_DIM + "─" * 60 + _RESET)
        return lines

    def _format_result(self, result: WatchResult) -> List[str]:
        """Return formatted lines for a single :class:`~pipewatch.watcher.WatchResult`."""
        lines: List[str] = []
        target_status = result.metric.status
        icon = _colour_status(target_status, _status_icon(target_status))
        target_line = (
            f"  {icon}  {_BOLD}{result.target.name}{_RESET}"
            f"  {_DIM}[{result.target.metric_key}]{_RESET}"
        )
        lines.append(target_line)

        value_str = f"{result.metric.value:.4g}" if result.metric.value is not None else "n/a"
        status_coloured = _colour_status(target_status, result.metric.status.value)
        lines.append(
            f"       value={_CYAN}{value_str}{_RESET}  status={status_coloured}"
        )

        if result.has_alerts():
            for event in result.alert_events:
                lines.append(f"       {_YELLOW}⚑ alert:{_RESET} {event}")

        return lines
