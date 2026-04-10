"""reporter.py — Formats and outputs pipeline health summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pipewatch.metrics import MetricStatus
from pipewatch.watcher import WatchResult


_STATUS_SYMBOLS = {
    MetricStatus.OK: "✓",
    MetricStatus.WARNING: "!",
    MetricStatus.CRITICAL: "✗",
}

_STATUS_LABELS = {
    MetricStatus.OK: "OK",
    MetricStatus.WARNING: "WARNING",
    MetricStatus.CRITICAL: "CRITICAL",
}


@dataclass
class Report:
    """Aggregated health report for one or more watch results."""

    results: List[WatchResult]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_critical(self) -> bool:
        return any(
            r.result.status == MetricStatus.CRITICAL
            for r in self.results
        )

    @property
    def has_warnings(self) -> bool:
        return any(
            r.result.status == MetricStatus.WARNING
            for r in self.results
        )

    @property
    def overall_status(self) -> MetricStatus:
        if self.has_critical:
            return MetricStatus.CRITICAL
        if self.has_warnings:
            return MetricStatus.WARNING
        return MetricStatus.OK


def format_report(report: Report, *, verbose: bool = False) -> str:
    """Return a human-readable string summary of *report*."""
    lines: List[str] = []
    ts = report.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"PipeWatch Report  [{ts}]")
    lines.append("-" * 50)

    for wr in report.results:
        metric = wr.target.metric
        status = wr.result.status
        symbol = _STATUS_SYMBOLS[status]
        label = _STATUS_LABELS[status]
        lines.append(f"  {symbol} [{label:8s}]  {metric.name}  (value={metric.value})")
        if verbose and wr.has_alerts:
            for alert in wr.alerts:
                lines.append(f"             → {alert}")

    lines.append("-" * 50)
    overall = _STATUS_LABELS[report.overall_status]
    lines.append(f"Overall: {overall}  ({len(report.results)} metric(s) checked)")
    return "\n".join(lines)
