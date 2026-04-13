"""Tests for pipewatch.rollup_reporter."""
from datetime import datetime, timezone, timedelta
import json

from pipewatch.rollup import RollupResult, RollupWindow
from pipewatch.rollup_reporter import RollupReporter

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_window(metric_key="cpu", count=3, mean=55.0, minimum=40.0, maximum=70.0):
    return RollupWindow(
        start=T0,
        end=T0 + timedelta(seconds=300),
        metric_key=metric_key,
        count=count,
        mean=mean,
        minimum=minimum,
        maximum=maximum,
    )


def _make_result(metric_key="cpu", windows=None):
    return RollupResult(
        metric_key=metric_key,
        windows=windows if windows is not None else [_make_window(metric_key)],
    )


class TestRollupReporterText:
    def test_empty_results_message(self):
        reporter = RollupReporter([])
        assert "No rollup" in reporter.format_text()

    def test_empty_windows_message(self):
        reporter = RollupReporter([RollupResult(metric_key="cpu", windows=[])])
        assert "No rollup" in reporter.format_text()

    def test_contains_metric_key(self):
        reporter = RollupReporter([_make_result("latency_ms")])
        assert "latency_ms" in reporter.format_text()

    def test_contains_mean(self):
        reporter = RollupReporter([_make_result(windows=[_make_window(mean=88.5)])])
        assert "88.5" in reporter.format_text()

    def test_contains_count(self):
        reporter = RollupReporter([_make_result(windows=[_make_window(count=7)])])
        assert "n=7" in reporter.format_text()

    def test_has_results_false_when_no_windows(self):
        reporter = RollupReporter([RollupResult(metric_key="x", windows=[])])
        assert reporter.has_results() is False

    def test_has_results_true_when_windows_present(self):
        reporter = RollupReporter([_make_result()])
        assert reporter.has_results() is True


class TestRollupReporterJson:
    def test_json_is_valid(self):
        reporter = RollupReporter([_make_result()])
        data = json.loads(reporter.format_json())
        assert isinstance(data, list)

    def test_json_contains_metric_key(self):
        reporter = RollupReporter([_make_result("error_rate")])
        data = json.loads(reporter.format_json())
        assert data[0]["metric_key"] == "error_rate"

    def test_json_windows_list(self):
        reporter = RollupReporter([_make_result(windows=[_make_window(), _make_window()])])
        data = json.loads(reporter.format_json())
        assert len(data[0]["windows"]) == 2

    def test_json_window_has_required_fields(self):
        reporter = RollupReporter([_make_result()])
        data = json.loads(reporter.format_json())
        w = data[0]["windows"][0]
        for key in ("start", "end", "count", "mean", "min", "max"):
            assert key in w
