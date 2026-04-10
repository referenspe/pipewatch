"""Tests for pipewatch.formatter."""
from __future__ import annotations

import json
import pytest

from pipewatch.metrics import PipelineMetric, MetricStatus
from pipewatch.watcher import WatchResult
from pipewatch.reporter import Report
from pipewatch.formatter import TextFormatter, JsonFormatter, get_formatter


def _make_result(name: str, value: float, status: MetricStatus) -> WatchResult:
    metric = PipelineMetric(name=name, value=value, unit="ms")
    return WatchResult(metric=metric, status=status)


@pytest.fixture()
def mixed_report() -> Report:
    return Report(
        results=[
            _make_result("latency", 120.0, MetricStatus.OK),
            _make_result("error_rate", 5.5, MetricStatus.WARNING),
            _make_result("queue_depth", 999.0, MetricStatus.CRITICAL),
        ]
    )


class TestTextFormatter:
    def test_contains_overall_critical(self, mixed_report: Report) -> None:
        output = TextFormatter().format(mixed_report)
        assert "CRITICAL" in output

    def test_contains_all_metric_names(self, mixed_report: Report) -> None:
        output = TextFormatter().format(mixed_report)
        assert "latency" in output
        assert "error_rate" in output
        assert "queue_depth" in output

    def test_contains_status_symbols(self, mixed_report: Report) -> None:
        output = TextFormatter().format(mixed_report)
        assert "✓" in output
        assert "⚠" in output
        assert "✗" in output

    def test_ok_report_shows_ok_overall(self) -> None:
        report = Report(results=[_make_result("cpu", 10.0, MetricStatus.OK)])
        output = TextFormatter().format(report)
        assert "OK" in output


class TestJsonFormatter:
    def test_valid_json(self, mixed_report: Report) -> None:
        output = JsonFormatter().format(mixed_report)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_overall_status_key(self, mixed_report: Report) -> None:
        data = json.loads(JsonFormatter().format(mixed_report))
        assert data["overall_status"] == "CRITICAL"

    def test_results_length(self, mixed_report: Report) -> None:
        data = json.loads(JsonFormatter().format(mixed_report))
        assert len(data["results"]) == 3

    def test_result_fields(self, mixed_report: Report) -> None:
        data = json.loads(JsonFormatter().format(mixed_report))
        first = data["results"][0]
        assert "metric" in first
        assert "value" in first
        assert "unit" in first
        assert "status" in first


class TestGetFormatter:
    def test_returns_text_formatter(self) -> None:
        assert isinstance(get_formatter("text"), TextFormatter)

    def test_returns_json_formatter(self) -> None:
        assert isinstance(get_formatter("json"), JsonFormatter)

    def test_raises_on_unknown(self) -> None:
        with pytest.raises(ValueError, match="Unknown formatter"):
            get_formatter("xml")
