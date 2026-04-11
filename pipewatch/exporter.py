"""Metric exporter: serialise pipeline state to JSON or CSV for external consumers."""

from __future__ import annotations

import csv
import io
import json
from typing import List

from pipewatch.aggregator import MetricSummary
from pipewatch.reporter import Report


class MetricExporter:
    """Converts a Report (and optional summaries) into exportable formats."""

    def __init__(self, report: Report, summaries: List[MetricSummary] | None = None) -> None:
        self.report = report
        self.summaries = summaries or []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON string representing the full export payload."""
        return json.dumps(self._build_payload(), indent=indent)

    def to_csv(self) -> str:
        """Return a CSV string with one row per watch-result metric."""
        output = io.StringIO()
        fieldnames = ["target", "metric_key", "value", "status", "min", "max", "mean", "count"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in self._build_rows():
            writer.writerow(row)
        return output.getvalue()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self) -> dict:
        results = []
        summary_index = {s.metric_key: s for s in self.summaries}
        for wr in self.report.results:
            metric = wr.metric
            summary = summary_index.get(metric.key)
            entry = {
                "target": wr.target.name,
                "metric_key": metric.key,
                "value": metric.value,
                "status": metric.status.value,
            }
            if summary is not None:
                entry["summary"] = summary.to_dict()
            results.append(entry)
        return {
            "overall_status": self.report.overall_status().value,
            "results": results,
        }

    def _build_rows(self) -> List[dict]:
        summary_index = {s.metric_key: s for s in self.summaries}
        rows = []
        for wr in self.report.results:
            metric = wr.metric
            summary = summary_index.get(metric.key)
            rows.append({
                "target": wr.target.name,
                "metric_key": metric.key,
                "value": metric.value,
                "status": metric.status.value,
                "min": summary.min_value if summary else "",
                "max": summary.max_value if summary else "",
                "mean": round(summary.mean_value, 4) if summary else "",
                "count": summary.count if summary else "",
            })
        return rows
