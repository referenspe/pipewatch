"""Tests for pipewatch.aggregator."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from pipewatch.aggregator import MetricAggregator, MetricSummary
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig


def _make_metric(key: str, value: float, status: MetricStatus) -> PipelineMetric:
    cfg = ThresholdConfig(warning=50.0, critical=90.0)
    return PipelineMetric(key=key, value=value, threshold=cfg, status=status)


def _populated_history(entries) -> MetricHistory:
    """entries: list of (key, value, status) tuples."""
    h = MetricHistory()
    for key, value, status in entries:
        h.record(_make_metric(key, value, status))
    return h


class TestMetricAggregatorSummarize:
    def test_returns_none_for_unknown_key(self):
        agg = MetricAggregator()
        h = MetricHistory()
        assert agg.summarize(h, "missing") is None

    def test_count_matches_recorded_entries(self):
        h = _populated_history([("cpu", v, MetricStatus.OK) for v in [10, 20, 30]])
        summary = MetricAggregator().summarize(h, "cpu")
        assert summary.count == 3

    def test_min_max_correct(self):
        h = _populated_history([("cpu", v, MetricStatus.OK) for v in [10, 40, 70]])
        summary = MetricAggregator().summarize(h, "cpu")
        assert summary.min_value == 10
        assert summary.max_value == 70

    def test_mean_correct(self):
        h = _populated_history([("cpu", v, MetricStatus.OK) for v in [10, 20, 30]])
        summary = MetricAggregator().summarize(h, "cpu")
        assert summary.mean_value == pytest.approx(20.0)

    def test_stddev_zero_for_single_entry(self):
        h = _populated_history([("cpu", 42.0, MetricStatus.OK)])
        summary = MetricAggregator().summarize(h, "cpu")
        assert summary.stddev_value == 0.0

    def test_alert_count_excludes_ok(self):
        entries = [
            ("lag", 10.0, MetricStatus.OK),
            ("lag", 60.0, MetricStatus.WARNING),
            ("lag", 95.0, MetricStatus.CRITICAL),
        ]
        h = _populated_history(entries)
        summary = MetricAggregator().summarize(h, "lag")
        assert summary.alert_count == 2

    def test_latest_status_reflects_last_recorded(self):
        entries = [
            ("lag", 10.0, MetricStatus.OK),
            ("lag", 95.0, MetricStatus.CRITICAL),
        ]
        h = _populated_history(entries)
        summary = MetricAggregator().summarize(h, "lag")
        assert summary.latest_status == MetricStatus.CRITICAL

    def test_to_dict_contains_expected_keys(self):
        h = _populated_history([("cpu", 30.0, MetricStatus.OK)])
        d = MetricAggregator().summarize(h, "cpu").to_dict()
        for key in ("metric_key", "count", "min", "max", "mean", "median", "stddev", "latest_status", "alert_count"):
            assert key in d


class TestMetricAggregatorSummarizeAll:
    def test_returns_summary_per_key(self):
        h = _populated_history([
            ("cpu", 10.0, MetricStatus.OK),
            ("mem", 80.0, MetricStatus.WARNING),
        ])
        summaries = MetricAggregator().summarize_all(h)
        keys = {s.metric_key for s in summaries}
        assert keys == {"cpu", "mem"}

    def test_empty_history_returns_empty_list(self):
        h = MetricHistory()
        assert MetricAggregator().summarize_all(h) == []
