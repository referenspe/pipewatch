"""Aggregates metric history into summary statistics for reporting."""

from dataclasses import dataclass, field
from typing import List, Optional
from statistics import mean, median, stdev

from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.metrics import MetricStatus


@dataclass
class MetricSummary:
    """Summary statistics for a single metric over a time window."""

    metric_key: str
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    stddev_value: float
    latest_status: MetricStatus
    alert_count: int  # number of snapshots with WARNING or CRITICAL

    def to_dict(self) -> dict:
        return {
            "metric_key": self.metric_key,
            "count": self.count,
            "min": self.min_value,
            "max": self.max_value,
            "mean": round(self.mean_value, 4),
            "median": round(self.median_value, 4),
            "stddev": round(self.stddev_value, 4),
            "latest_status": self.latest_status.value,
            "alert_count": self.alert_count,
        }


class MetricAggregator:
    """Computes summary statistics from a MetricHistory instance."""

    def summarize(self, history: MetricHistory, metric_key: str) -> Optional[MetricSummary]:
        """Return a MetricSummary for the given metric key, or None if no data."""
        snapshots: List[MetricSnapshot] = history.all(metric_key)
        if not snapshots:
            return None

        values = [s.value for s in snapshots]
        alert_statuses = {MetricStatus.WARNING, MetricStatus.CRITICAL}
        alert_count = sum(1 for s in snapshots if s.status in alert_statuses)
        latest = snapshots[-1]

        std = stdev(values) if len(values) > 1 else 0.0

        return MetricSummary(
            metric_key=metric_key,
            count=len(values),
            min_value=min(values),
            max_value=max(values),
            mean_value=mean(values),
            median_value=median(values),
            stddev_value=std,
            latest_status=latest.status,
            alert_count=alert_count,
        )

    def summarize_all(self, history: MetricHistory) -> List[MetricSummary]:
        """Return summaries for every metric key tracked in the history."""
        summaries = []
        for key in history.keys():
            summary = self.summarize(history, key)
            if summary is not None:
                summaries.append(summary)
        return summaries
