"""Tests for pipewatch.anomaly_reporter."""

import json

import pytest

from pipewatch.anomaly import AnomalyLevel, AnomalyResult
from pipewatch.anomaly_reporter import AnomalyReporter


def _make_result(key="latency", z=0.5, level=AnomalyLevel.NONE) -> AnomalyResult:
    return AnomalyResult(
        metric_key=key,
        value=12.5,
        mean=10.0,
        std_dev=5.0,
        z_score=z,
        level=level,
    )


class TestAnomalyReporterText:
    def test_empty_results_message(self):
        r = AnomalyReporter([])
        assert "No anomaly" in r.format_text()

    def test_contains_metric_key(self):
        r = AnomalyReporter([_make_result(key="cpu_usage")])
        assert "cpu_usage" in r.format_text()

    def test_contains_level_label_mild(self):
        r = AnomalyReporter([_make_result(level=AnomalyLevel.MILD)])
        assert "MILD" in r.format_text()

    def test_contains_level_label_severe(self):
        r = AnomalyReporter([_make_result(level=AnomalyLevel.SEVERE)])
        assert "SEVERE" in r.format_text()

    def test_contains_z_score(self):
        r = AnomalyReporter([_make_result(z=2.75)])
        assert "2.75" in r.format_text()


class TestAnomalyReporterJson:
    def test_returns_valid_json(self):
        r = AnomalyReporter([_make_result()])
        parsed = json.loads(r.format_json())
        assert isinstance(parsed, list)

    def test_json_contains_metric_key(self):
        r = AnomalyReporter([_make_result(key="queue_depth")])
        parsed = json.loads(r.format_json())
        assert parsed[0]["metric_key"] == "queue_depth"

    def test_empty_returns_empty_list(self):
        r = AnomalyReporter([])
        parsed = json.loads(r.format_json())
        assert parsed == []


class TestAnomalyReporterFlags:
    def test_has_anomalies_false_when_all_none(self):
        r = AnomalyReporter([_make_result(level=AnomalyLevel.NONE)])
        assert not r.has_anomalies()

    def test_has_anomalies_true_when_mild(self):
        r = AnomalyReporter([_make_result(level=AnomalyLevel.MILD)])
        assert r.has_anomalies()

    def test_has_severe_false_when_only_mild(self):
        r = AnomalyReporter([_make_result(level=AnomalyLevel.MILD)])
        assert not r.has_severe()

    def test_has_severe_true_when_severe_present(self):
        r = AnomalyReporter([_make_result(level=AnomalyLevel.SEVERE)])
        assert r.has_severe()
