"""Tests for pipewatch.reporter."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.reporter import Report, format_report
from pipewatch.watcher import WatchResult, WatchTarget


def _make_watch_result(name: str, value: float, warning: float, critical: float) -> WatchResult:
    config = ThresholdConfig(warning=warning, critical=critical)
    metric = PipelineMetric(name=name, value=value)
    target = WatchTarget(metric=metric, threshold=config)
    eval_result = config.evaluate(metric)
    alerts = []
    return WatchResult(target=target, result=eval_result, alerts=alerts)


class TestReport:
    def test_overall_ok_when_all_ok(self):
        wr = _make_watch_result("latency", 10.0, 50.0, 100.0)
        report = Report(results=[wr])
        assert report.overall_status == MetricStatus.OK

    def test_overall_warning_when_any_warning(self):
        ok_wr = _make_watch_result("latency", 10.0, 50.0, 100.0)
        warn_wr = _make_watch_result("error_rate", 60.0, 50.0, 100.0)
        report = Report(results=[ok_wr, warn_wr])
        assert report.overall_status == MetricStatus.WARNING
        assert report.has_warnings
        assert not report.has_critical

    def test_overall_critical_when_any_critical(self):
        warn_wr = _make_watch_result("error_rate", 60.0, 50.0, 100.0)
        crit_wr = _make_watch_result("queue_depth", 150.0, 50.0, 100.0)
        report = Report(results=[warn_wr, crit_wr])
        assert report.overall_status == MetricStatus.CRITICAL
        assert report.has_critical

    def test_generated_at_defaults_to_now(self):
        before = datetime.utcnow()
        report = Report(results=[])
        after = datetime.utcnow()
        assert before <= report.generated_at <= after


class TestFormatReport:
    def test_contains_metric_name(self):
        wr = _make_watch_result("throughput", 5.0, 10.0, 20.0)
        report = Report(results=[wr])
        output = format_report(report)
        assert "throughput" in output

    def test_contains_status_label(self):
        wr = _make_watch_result("latency", 75.0, 50.0, 100.0)
        report = Report(results=[wr])
        output = format_report(report)
        assert "WARNING" in output

    def test_contains_overall_status(self):
        wr = _make_watch_result("latency", 5.0, 50.0, 100.0)
        report = Report(results=[wr])
        output = format_report(report)
        assert "Overall: OK" in output

    def test_verbose_shows_alerts(self):
        wr = _make_watch_result("error_rate", 120.0, 50.0, 100.0)
        mock_alert = MagicMock()
        mock_alert.__str__ = lambda self: "CRITICAL alert fired"
        wr.alerts.append(mock_alert)
        report = Report(results=[wr])
        output = format_report(report, verbose=True)
        assert "CRITICAL alert fired" in output

    def test_non_verbose_hides_alerts(self):
        wr = _make_watch_result("error_rate", 120.0, 50.0, 100.0)
        mock_alert = MagicMock()
        mock_alert.__str__ = lambda self: "secret alert"
        wr.alerts.append(mock_alert)
        report = Report(results=[wr])
        output = format_report(report, verbose=False)
        assert "secret alert" not in output
