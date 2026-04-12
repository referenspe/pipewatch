"""Tests for pipewatch.replay_reporter."""
from __future__ import annotations

import datetime
import json

import pytest

from pipewatch.history import MetricSnapshot
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.replay import ReplayEvent, ReplayResult
from pipewatch.replay_reporter import ReplayReporter


def _make_threshold():
    return ThresholdConfig(warning=70.0, critical=90.0)


def _make_event(value: float, status: MetricStatus) -> ReplayEvent:
    snap = MetricSnapshot(
        key="latency",
        value=value,
        timestamp=datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc),
    )
    metric = PipelineMetric(
        key="latency",
        value=value,
        status=status,
        threshold=_make_threshold(),
    )
    return ReplayEvent(snapshot=snap, metric=metric)


def _make_result(events=None, stopped_early=False) -> ReplayResult:
    result = ReplayResult(key="latency", stopped_early=stopped_early)
    result.events = events or []
    return result


class TestReplayReporterText:
    def test_empty_results_message(self):
        reporter = ReplayReporter([])
        assert "No replay results" in reporter.format_text()

    def test_contains_key(self):
        result = _make_result()
        reporter = ReplayReporter([result])
        assert "latency" in reporter.format_text()

    def test_contains_counts(self):
        events = [
            _make_event(95.0, MetricStatus.CRITICAL),
            _make_event(75.0, MetricStatus.WARNING),
        ]
        result = _make_result(events=events)
        text = ReplayReporter([result]).format_text()
        assert "Critical" in text
        assert "Warning" in text

    def test_stopped_early_label(self):
        result = _make_result(stopped_early=True)
        text = ReplayReporter([result]).format_text()
        assert "stopped early" in text

    def test_has_criticals_true(self):
        events = [_make_event(95.0, MetricStatus.CRITICAL)]
        result = _make_result(events=events)
        reporter = ReplayReporter([result])
        assert reporter.has_criticals() is True

    def test_has_criticals_false(self):
        result = _make_result()
        reporter = ReplayReporter([result])
        assert reporter.has_criticals() is False

    def test_has_warnings_true(self):
        events = [_make_event(75.0, MetricStatus.WARNING)]
        result = _make_result(events=events)
        reporter = ReplayReporter([result])
        assert reporter.has_warnings() is True


class TestReplayReporterJson:
    def test_format_json_is_valid(self):
        events = [_make_event(10.0, MetricStatus.OK)]
        result = _make_result(events=events)
        raw = ReplayReporter([result]).format_json()
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert parsed[0]["key"] == "latency"

    def test_format_json_empty(self):
        raw = ReplayReporter([]).format_json()
        assert json.loads(raw) == []
