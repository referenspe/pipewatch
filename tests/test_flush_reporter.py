"""Tests for pipewatch.flush_reporter."""
from pipewatch.flush import FlushResult
from pipewatch.flush_reporter import FlushReporter


def _make_result(flushed=5, remaining=0, triggered_by="manual"):
    return FlushResult(flushed_count=flushed, remaining_count=remaining, triggered_by=triggered_by)


class TestFlushReporterText:
    def test_empty_results_message(self):
        r = FlushReporter([])
        assert "No flush" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert FlushReporter([]).has_results is False

    def test_has_results_true_when_populated(self):
        assert FlushReporter([_make_result()]).has_results is True

    def test_contains_triggered_by(self):
        r = FlushReporter([_make_result(triggered_by="critical")])
        assert "critical" in r.format_text()

    def test_contains_flushed_count(self):
        r = FlushReporter([_make_result(flushed=7)])
        assert "7" in r.format_text()

    def test_total_flushed_sums_all(self):
        r = FlushReporter([_make_result(flushed=3), _make_result(flushed=4)])
        assert r.total_flushed == 7

    def test_total_flushed_empty(self):
        assert FlushReporter([]).total_flushed == 0

    def test_format_json_returns_list(self):
        r = FlushReporter([_make_result()])
        data = r.format_json()
        assert isinstance(data, list)
        assert data[0]["triggered_by"] == "manual"

    def test_format_json_empty(self):
        assert FlushReporter([]).format_json() == []

    def test_multiple_events_all_present(self):
        r = FlushReporter([
            _make_result(triggered_by="threshold"),
            _make_result(triggered_by="interval"),
        ])
        text = r.format_text()
        assert "threshold" in text
        assert "interval" in text
