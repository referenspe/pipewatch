"""Tests for pipewatch.trend_reporter."""

from __future__ import annotations

import json

import pytest

from pipewatch.trend import TrendDirection, TrendResult
from pipewatch.trend_reporter import TrendReporter


def _make_result(
    key: str = "cpu",
    direction: TrendDirection = TrendDirection.RISING,
    slope: float | None = 1.5,
    sample_count: int = 5,
) -> TrendResult:
    return TrendResult(key=key, direction=direction, slope=slope, sample_count=sample_count)


class TestTrendReporterText:
    def test_empty_results_message(self):
        reporter = TrendReporter()
        output = reporter.format_text([])
        assert "No trend data" in output

    def test_contains_metric_key(self):
        reporter = TrendReporter()
        result = _make_result(key="latency")
        output = reporter.format_text([result])
        assert "latency" in output

    def test_contains_direction(self):
        reporter = TrendReporter()
        result = _make_result(direction=TrendDirection.FALLING)
        output = reporter.format_text([result])
        assert "falling" in output

    def test_contains_slope(self):
        reporter = TrendReporter()
        result = _make_result(slope=2.5)
        output = reporter.format_text([result])
        assert "2.5" in output

    def test_unknown_slope_shows_na(self):
        reporter = TrendReporter()
        result = _make_result(slope=None, direction=TrendDirection.UNKNOWN)
        output = reporter.format_text([result])
        assert "n/a" in output

    def test_contains_sample_count(self):
        reporter = TrendReporter()
        result = _make_result(sample_count=7)
        output = reporter.format_text([result])
        assert "7" in output


class TestTrendReporterJson:
    def test_returns_valid_json(self):
        reporter = TrendReporter()
        result = _make_result()
        output = reporter.format_json([result])
        parsed = json.loads(output)
        assert isinstance(parsed, list)

    def test_json_contains_key(self):
        reporter = TrendReporter()
        result = _make_result(key="mem")
        parsed = json.loads(reporter.format_json([result]))
        assert parsed[0]["key"] == "mem"

    def test_json_direction_is_string(self):
        reporter = TrendReporter()
        result = _make_result(direction=TrendDirection.STABLE)
        parsed = json.loads(reporter.format_json([result]))
        assert parsed[0]["direction"] == "stable"


class TestTrendReporterHelpers:
    def test_has_rising_true(self):
        reporter = TrendReporter()
        results = [_make_result(direction=TrendDirection.RISING)]
        assert reporter.has_rising(results) is True

    def test_has_rising_false(self):
        reporter = TrendReporter()
        results = [_make_result(direction=TrendDirection.STABLE)]
        assert reporter.has_rising(results) is False

    def test_has_falling_true(self):
        reporter = TrendReporter()
        results = [_make_result(direction=TrendDirection.FALLING)]
        assert reporter.has_falling(results) is True

    def test_filter_by_direction(self):
        reporter = TrendReporter()
        results = [
            _make_result(key="a", direction=TrendDirection.RISING),
            _make_result(key="b", direction=TrendDirection.STABLE),
            _make_result(key="c", direction=TrendDirection.RISING),
        ]
        filtered = reporter.filter_by_direction(results, TrendDirection.RISING)
        assert len(filtered) == 2
        assert all(r.direction == TrendDirection.RISING for r in filtered)
