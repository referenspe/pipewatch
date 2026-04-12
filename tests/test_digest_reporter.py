"""Tests for pipewatch.digest_reporter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from pipewatch.digest import Digest, DigestEntry
from pipewatch.digest_reporter import DigestReporter
from pipewatch.metrics import MetricStatus

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_summary(mean: float = 3.14):
    s = MagicMock()
    s.mean = mean
    s.count = 10
    s.to_dict.return_value = {"mean": mean, "count": 10}
    return s


def _make_digest(entries=None):
    return Digest(
        title="Test Digest",
        generated_at=_NOW,
        entries=entries or [],
    )


class TestDigestReporterText:
    def test_empty_entries_message(self):
        reporter = DigestReporter(_make_digest())
        assert "no entries" in reporter.format_text()

    def test_contains_title(self):
        reporter = DigestReporter(_make_digest())
        assert "Test Digest" in reporter.format_text()

    def test_contains_metric_key(self):
        entry = DigestEntry("pipeline.lag", MetricStatus.WARNING, _make_summary())
        reporter = DigestReporter(_make_digest([entry]))
        assert "pipeline.lag" in reporter.format_text()

    def test_contains_status_label(self):
        entry = DigestEntry("m", MetricStatus.CRITICAL, _make_summary())
        reporter = DigestReporter(_make_digest([entry]))
        assert "CRIT" in reporter.format_text()

    def test_contains_mean_value(self):
        entry = DigestEntry("m", MetricStatus.WARNING, _make_summary(mean=42.0))
        reporter = DigestReporter(_make_digest([entry]))
        assert "42" in reporter.format_text()

    def test_has_alerts_true_when_critical(self):
        entry = DigestEntry("m", MetricStatus.CRITICAL, _make_summary())
        reporter = DigestReporter(_make_digest([entry]))
        assert reporter.has_alerts() is True

    def test_has_alerts_false_when_all_ok(self):
        reporter = DigestReporter(_make_digest())
        assert reporter.has_alerts() is False


class TestDigestReporterJson:
    def test_valid_json(self):
        reporter = DigestReporter(_make_digest())
        data = json.loads(reporter.format_json())
        assert isinstance(data, dict)

    def test_json_contains_title(self):
        reporter = DigestReporter(_make_digest())
        data = json.loads(reporter.format_json())
        assert data["title"] == "Test Digest"

    def test_json_contains_overall_status(self):
        entry = DigestEntry("m", MetricStatus.WARNING, _make_summary())
        reporter = DigestReporter(_make_digest([entry]))
        data = json.loads(reporter.format_json())
        assert data["overall_status"] == "warning"

    def test_json_entries_list(self):
        entry = DigestEntry("x", MetricStatus.OK, _make_summary())
        reporter = DigestReporter(_make_digest([entry]))
        data = json.loads(reporter.format_json())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["metric_key"] == "x"
