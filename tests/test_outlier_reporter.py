"""Tests for pipewatch.outlier_reporter."""
import json

from pipewatch.metrics import MetricStatus
from pipewatch.outlier import OutlierResult
from pipewatch.outlier_reporter import OutlierReporter


def _make_result(
    key: str = "pipe.queue",
    value: float = 10.0,
    status: MetricStatus = MetricStatus.OK,
) -> OutlierResult:
    return OutlierResult(
        metric_key=key,
        value=value,
        q1=8.0,
        q3=12.0,
        iqr=4.0,
        lower_fence=2.0,
        upper_fence=18.0,
        status=status,
    )


class TestOutlierReporterText:
    def test_empty_results_message(self):
        reporter = OutlierReporter([])
        assert "no results" in reporter.format_text()

    def test_has_results_false_when_empty(self):
        assert OutlierReporter([]).has_results() is False

    def test_has_results_true_when_populated(self):
        assert OutlierReporter([_make_result()]).has_results() is True

    def test_contains_metric_key(self):
        reporter = OutlierReporter([_make_result(key="pipe.queue")])
        assert "pipe.queue" in reporter.format_text()

    def test_contains_status_label(self):
        reporter = OutlierReporter([_make_result(status=MetricStatus.WARNING)])
        assert "WARNING" in reporter.format_text()

    def test_contains_value(self):
        reporter = OutlierReporter([_make_result(value=42.5)])
        assert "42.5" in reporter.format_text()

    def test_has_outliers_false_when_all_ok(self):
        reporter = OutlierReporter([_make_result(status=MetricStatus.OK)])
        assert reporter.has_outliers() is False

    def test_has_outliers_true_when_warning(self):
        reporter = OutlierReporter([_make_result(status=MetricStatus.WARNING)])
        assert reporter.has_outliers() is True

    def test_has_critical_true_when_critical(self):
        reporter = OutlierReporter([_make_result(status=MetricStatus.CRITICAL)])
        assert reporter.has_critical() is True

    def test_has_critical_false_when_only_warning(self):
        reporter = OutlierReporter([_make_result(status=MetricStatus.WARNING)])
        assert reporter.has_critical() is False

    def test_outlier_results_filters_ok(self):
        results = [
            _make_result(key="a", status=MetricStatus.OK),
            _make_result(key="b", status=MetricStatus.WARNING),
        ]
        reporter = OutlierReporter(results)
        filtered = reporter.outlier_results()
        assert len(filtered) == 1
        assert filtered[0].metric_key == "b"

    def test_format_json_is_valid(self):
        reporter = OutlierReporter([_make_result()])
        parsed = json.loads(reporter.format_json())
        assert isinstance(parsed, list)
        assert parsed[0]["metric_key"] == "pipe.queue"
