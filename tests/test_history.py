"""Tests for pipewatch.history."""
from __future__ import annotations

import pytest

from pipewatch.history import HistoryStore, MetricHistory, MetricSnapshot
from pipewatch.metrics import MetricStatus, PipelineMetric


def _make_metric(key: str = "queue.depth", value: float = 10.0,
                 status: MetricStatus = MetricStatus.OK) -> PipelineMetric:
    return PipelineMetric(key=key, value=value, status=status)


class TestMetricHistory:
    def test_record_stores_snapshot(self):
        h = MetricHistory(metric_key="q")
        h.record(_make_metric(value=5.0))
        assert len(h.snapshots()) == 1
        assert h.snapshots()[0].value == 5.0

    def test_latest_returns_most_recent(self):
        h = MetricHistory(metric_key="q")
        h.record(_make_metric(value=1.0))
        h.record(_make_metric(value=2.0))
        assert h.latest().value == 2.0

    def test_latest_returns_none_when_empty(self):
        h = MetricHistory(metric_key="q")
        assert h.latest() is None

    def test_max_entries_evicts_oldest(self):
        h = MetricHistory(metric_key="q", max_entries=3)
        for v in [1.0, 2.0, 3.0, 4.0]:
            h.record(_make_metric(value=v))
        assert len(h.snapshots()) == 3
        assert h.snapshots()[0].value == 2.0

    def test_values_returns_list_of_floats(self):
        h = MetricHistory(metric_key="q")
        for v in [10.0, 20.0, 30.0]:
            h.record(_make_metric(value=v))
        assert h.values() == [10.0, 20.0, 30.0]

    def test_average_correct(self):
        h = MetricHistory(metric_key="q")
        for v in [10.0, 20.0, 30.0]:
            h.record(_make_metric(value=v))
        assert h.average() == pytest.approx(20.0)

    def test_average_none_when_empty(self):
        assert MetricHistory(metric_key="q").average() is None

    def test_consecutive_status_count_all_match(self):
        h = MetricHistory(metric_key="q")
        for _ in range(4):
            h.record(_make_metric(status=MetricStatus.WARNING))
        assert h.consecutive_status_count(MetricStatus.WARNING) == 4

    def test_consecutive_status_count_partial(self):
        h = MetricHistory(metric_key="q")
        h.record(_make_metric(status=MetricStatus.OK))
        h.record(_make_metric(status=MetricStatus.WARNING))
        h.record(_make_metric(status=MetricStatus.WARNING))
        assert h.consecutive_status_count(MetricStatus.WARNING) == 2
        assert h.consecutive_status_count(MetricStatus.OK) == 0


class TestHistoryStore:
    def test_record_creates_history_for_new_key(self):
        store = HistoryStore()
        store.record(_make_metric(key="a"))
        assert store.get("a") is not None

    def test_get_returns_none_for_unknown_key(self):
        store = HistoryStore()
        assert store.get("missing") is None

    def test_all_keys_lists_recorded_metrics(self):
        store = HistoryStore()
        store.record(_make_metric(key="x"))
        store.record(_make_metric(key="y"))
        assert set(store.all_keys()) == {"x", "y"}

    def test_multiple_records_same_key(self):
        store = HistoryStore()
        store.record(_make_metric(key="k", value=1.0))
        store.record(_make_metric(key="k", value=2.0))
        assert len(store.get("k").snapshots()) == 2

    def test_max_entries_propagated(self):
        store = HistoryStore(max_entries=2)
        for v in [1.0, 2.0, 3.0]:
            store.record(_make_metric(key="k", value=v))
        assert len(store.get("k").snapshots()) == 2
