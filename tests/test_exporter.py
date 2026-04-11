"""Tests for pipewatch.exporter.MetricExporter."""

from __future__ import annotations

import csv
import io
import json

import pytest

from pipewatch.aggregator import MetricSummary
from pipewatch.exporter import MetricExporter
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.reporter import Report
from pipewatch.watcher import WatchResult, WatchTarget


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_threshold() -> ThresholdConfig:
    return ThresholdConfig(warning=50.0, critical=90.0)


def _make_metric(key: str, value: float, status: MetricStatus) -> PipelineMetric:
    m = PipelineMetric(key=key, value=value, threshold=_make_threshold())
    m._status = status  # bypass evaluation for simplicity
    return m


def _make_target(name: str) -> WatchTarget:
    return WatchTarget(name=name, metric_key="k", fetch=lambda: 0.0, threshold=_make_threshold())


def _make_result(target_name: str, key: str, value: float, status: MetricStatus) -> WatchResult:
    metric = _make_metric(key, value, status)
    target = _make_target(target_name)
    return WatchResult(target=target, metric=metric)


def _make_summary(key: str, count: int = 5) -> MetricSummary:
    return MetricSummary(
        metric_key=key,
        count=count,
        min_value=1.0,
        max_value=99.0,
        mean_value=50.0,
    )


@pytest.fixture()
def simple_report() -> Report:
    results = [
        _make_result("pipe-a", "latency", 30.0, MetricStatus.OK),
        _make_result("pipe-b", "error_rate", 75.0, MetricStatus.WARNING),
    ]
    return Report(results=results)


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

class TestToJson:
    def test_overall_status_present(self, simple_report):
        exporter = MetricExporter(simple_report)
        data = json.loads(exporter.to_json())
        assert "overall_status" in data

    def test_results_count_matches(self, simple_report):
        exporter = MetricExporter(simple_report)
        data = json.loads(exporter.to_json())
        assert len(data["results"]) == 2

    def test_metric_key_present_in_results(self, simple_report):
        exporter = MetricExporter(simple_report)
        data = json.loads(exporter.to_json())
        keys = {r["metric_key"] for r in data["results"]}
        assert "latency" in keys
        assert "error_rate" in keys

    def test_summary_embedded_when_provided(self, simple_report):
        summaries = [_make_summary("latency")]
        exporter = MetricExporter(simple_report, summaries=summaries)
        data = json.loads(exporter.to_json())
        latency_row = next(r for r in data["results"] if r["metric_key"] == "latency")
        assert "summary" in latency_row
        assert latency_row["summary"]["count"] == 5

    def test_no_summary_key_when_absent(self, simple_report):
        exporter = MetricExporter(simple_report)
        data = json.loads(exporter.to_json())
        for row in data["results"]:
            assert "summary" not in row


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

class TestToCsv:
    def test_csv_has_header_row(self, simple_report):
        exporter = MetricExporter(simple_report)
        reader = csv.DictReader(io.StringIO(exporter.to_csv()))
        assert "metric_key" in reader.fieldnames

    def test_csv_row_count_matches(self, simple_report):
        exporter = MetricExporter(simple_report)
        rows = list(csv.DictReader(io.StringIO(exporter.to_csv())))
        assert len(rows) == 2

    def test_csv_summary_columns_populated(self, simple_report):
        summaries = [_make_summary("latency")]
        exporter = MetricExporter(simple_report, summaries=summaries)
        rows = list(csv.DictReader(io.StringIO(exporter.to_csv())))
        latency_row = next(r for r in rows if r["metric_key"] == "latency")
        assert latency_row["mean"] == "50.0"
        assert latency_row["count"] == "5"

    def test_csv_summary_columns_empty_when_absent(self, simple_report):
        exporter = MetricExporter(simple_report)
        rows = list(csv.DictReader(io.StringIO(exporter.to_csv())))
        for row in rows:
            assert row["mean"] == ""
