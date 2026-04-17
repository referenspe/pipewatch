"""Tests for pipewatch.reaper_reporter."""
import json
from pipewatch.reaper import ReapResult
from pipewatch.reaper_reporter import ReaperReporter


def _make_result(key="pipe_a", age=65.0, critical=False):
    return ReapResult(key=key, last_seen=1000.0, age_seconds=age, is_critical=critical)


class TestReaperReporterText:
    def test_empty_results_message(self):
        r = ReaperReporter([])
        assert "no stale" in r.format_text()

    def test_contains_key_name(self):
        r = ReaperReporter([_make_result()])
        assert "pipe_a" in r.format_text()

    def test_stale_label_present(self):
        r = ReaperReporter([_make_result(critical=False)])
        assert "STALE" in r.format_text()

    def test_critical_label_present(self):
        r = ReaperReporter([_make_result(critical=True)])
        assert "CRITICAL" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert not ReaperReporter([]).has_results()

    def test_has_results_true_when_populated(self):
        assert ReaperReporter([_make_result()]).has_results()

    def test_has_critical_true(self):
        r = ReaperReporter([_make_result(critical=True)])
        assert r.has_critical()

    def test_has_critical_false(self):
        r = ReaperReporter([_make_result(critical=False)])
        assert not r.has_critical()

    def test_has_stale_true(self):
        r = ReaperReporter([_make_result(critical=False)])
        assert r.has_stale()

    def test_format_json_valid(self):
        r = ReaperReporter([_make_result()])
        data = json.loads(r.format_json())
        assert isinstance(data, list)
        assert data[0]["key"] == "pipe_a"
