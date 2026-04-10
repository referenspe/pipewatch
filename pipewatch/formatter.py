"""Output formatters for pipeline watch results."""
from __future__ import annotations

import json
from typing import Protocol

from pipewatch.reporter import Report
from pipewatch.metrics import MetricStatus


STATUS_SYMBOLS = {
    MetricStatus.OK: "✓",
    MetricStatus.WARNING: "⚠",
    MetricStatus.CRITICAL: "✗",
}

STATUS_LABELS = {
    MetricStatus.OK: "OK",
    MetricStatus.WARNING: "WARNING",
    MetricStatus.CRITICAL: "CRITICAL",
}


class OutputFormatter(Protocol):
    """Protocol for report formatters."""

    def format(self, report: Report) -> str:
        ...


class TextFormatter:
    """Renders a Report as a human-readable text table."""

    def format(self, report: Report) -> str:
        lines: list[str] = []
        overall = report.overall_status()
        symbol = STATUS_SYMBOLS[overall]
        label = STATUS_LABELS[overall]
        lines.append(f"Pipeline Report  [{symbol} {label}]")
        lines.append("-" * 50)
        for result in report.results:
            metric = result.metric
            status = result.status
            sym = STATUS_SYMBOLS[status]
            lbl = STATUS_LABELS[status]
            lines.append(
                f"  {sym} {metric.name:<30} {metric.value:>10.2f}  {lbl}"
            )
        lines.append("-" * 50)
        return "\n".join(lines)


class JsonFormatter:
    """Renders a Report as a JSON string."""

    def format(self, report: Report) -> str:
        overall = report.overall_status()
        payload = {
            "overall_status": STATUS_LABELS[overall],
            "results": [
                {
                    "metric": result.metric.name,
                    "value": result.metric.value,
                    "unit": result.metric.unit,
                    "status": STATUS_LABELS[result.status],
                }
                for result in report.results
            ],
        }
        return json.dumps(payload, indent=2)


def get_formatter(fmt: str) -> OutputFormatter:
    """Return a formatter instance by name ('text' or 'json')."""
    if fmt == "json":
        return JsonFormatter()
    if fmt == "text":
        return TextFormatter()
    raise ValueError(f"Unknown formatter: {fmt!r}. Choose 'text' or 'json'.")
