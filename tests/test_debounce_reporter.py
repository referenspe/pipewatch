"""Tests for pipewatch.debounce_reporter."""
import json

import pytest

from pipewatch.debounce import DebounceConfig, Debouncer, DebounceResult
from pipewatch.debounce_reporter import DebounceReporter
from pipewatch.metrics import MetricStatus


def _make_result(metric_key="cpu", status=MetricStatus.WARNING, consecutive=2, fired=True):
    return DebounceResult(
        metric_key=metric_key,
        status=status,
        consecutive=consecutive,
        fired=fired,
    )


class TestDebounceReporterText:
    def test_empty_results_message(self):
        r = DebounceReporter([])
        assert "no results" in r.format_text().lower()

    def test_contains_metric_key(self):
        r = DebounceReporter([_make_result(metric_key="latency")])
        assert "latency" in r.format_text()

    def test_fired_label_present(self):
        r = DebounceReporter([_make_result(fired=True)])
        assert "FIRED" in r.format_text()

    def test_pending_label_when_not_fired(self):
        r = DebounceReporter([_make_result(fired=False)])
        assert "pending" in r.format_text()

    def test_contains_consecutive_count(self):
        r = DebounceReporter([_make_result(consecutive=5)])
        assert "5" in r.format_text()


class TestDebounceReporterJson:
    def test_returns_valid_json(self):
        r = DebounceReporter([_make_result()])
        data = json.loads(r.format_json())
        assert isinstance(data, list)

    def test_json_contains_fired_field(self):
        r = DebounceReporter([_make_result(fired=True)])
        data = json.loads(r.format_json())
        assert data[0]["fired"] is True

    def test_json_contains_metric_key(self):
        r = DebounceReporter([_make_result(metric_key="throughput")])
        data = json.loads(r.format_json())
        assert data[0]["metric_key"] == "throughput"


class TestDebounceReporterHasFired:
    def test_has_fired_false_when_none_fired(self):
        r = DebounceReporter([_make_result(fired=False)])
        assert r.has_fired() is False

    def test_has_fired_true_when_any_fired(self):
        results = [_make_result(fired=False), _make_result(fired=True)]
        r = DebounceReporter(results)
        assert r.has_fired() is True

    def test_fired_results_filters_correctly(self):
        results = [
            _make_result(metric_key="a", fired=True),
            _make_result(metric_key="b", fired=False),
        ]
        r = DebounceReporter(results)
        fired = r.fired_results()
        assert len(fired) == 1
        assert fired[0].metric_key == "a"
