"""Tests for pipewatch.fanout_reporter."""
from __future__ import annotations

import json

import pytest

from pipewatch.fanout import FanoutResult
from pipewatch.fanout_reporter import FanoutReporter


def _make_result(
    metric_key: str = "m",
    sent=None,
    failed=None,
) -> FanoutResult:
    r = FanoutResult(metric_key=metric_key)
    r.sent = list(sent or [])
    r.failed = dict(failed or {})
    return r


class TestFanoutReporterText:
    def test_empty_results_message(self):
        rep = FanoutReporter([])
        assert "no dispatch" in FanoutReporter([]).format_text()

    def test_has_results_false_when_empty(self):
        assert FanoutReporter([]).has_results is False

    def test_has_results_true_when_populated(self):
        assert FanoutReporter([_make_result()]).has_results is True

    def test_contains_metric_key(self):
        rep = FanoutReporter([_make_result(metric_key="pipe.lag")])
        assert "pipe.lag" in rep.format_text()

    def test_ok_label_when_no_failures(self):
        rep = FanoutReporter([_make_result(sent=["slack"])])
        assert "OK" in rep.format_text()

    def test_fail_label_when_failures_present(self):
        rep = FanoutReporter([_make_result(failed={"email": "timeout"})])
        assert "FAIL" in rep.format_text()

    def test_failure_channel_and_error_shown(self):
        rep = FanoutReporter([_make_result(failed={"pagerduty": "auth error"})])
        text = rep.format_text()
        assert "pagerduty" in text
        assert "auth error" in text

    def test_total_sent_in_summary(self):
        results = [
            _make_result(sent=["a", "b"]),
            _make_result(sent=["c"]),
        ]
        rep = FanoutReporter(results)
        assert rep.total_sent == 3
        assert "total sent=3" in rep.format_text()

    def test_has_failures_true(self):
        rep = FanoutReporter([_make_result(failed={"x": "err"})])
        assert rep.has_failures is True

    def test_has_failures_false(self):
        rep = FanoutReporter([_make_result(sent=["a"])])
        assert rep.has_failures is False


class TestFanoutReporterJson:
    def test_valid_json(self):
        rep = FanoutReporter([_make_result(metric_key="k", sent=["a"])])
        data = json.loads(rep.format_json())
        assert "fanout_results" in data

    def test_json_total_sent(self):
        rep = FanoutReporter([_make_result(sent=["a", "b"])])
        data = json.loads(rep.format_json())
        assert data["total_sent"] == 2

    def test_json_total_failed(self):
        rep = FanoutReporter([_make_result(failed={"x": "e", "y": "f"})])
        data = json.loads(rep.format_json())
        assert data["total_failed"] == 2
