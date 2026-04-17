"""Tests for pipewatch.pause_reporter."""
from datetime import datetime, timezone

from pipewatch.pause import PauseResult
from pipewatch.pause_reporter import PauseReporter


def _ts():
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_result(key="pipe_a", paused=True, auto_resumed=False):
    return PauseResult(
        key=key,
        paused=paused,
        paused_at=_ts() if paused else None,
        resumed_at=None if paused else _ts(),
        auto_resumed=auto_resumed,
    )


class TestPauseReporterText:
    def test_empty_results_message(self):
        r = PauseReporter([])
        assert "No pause" in r.format_text()

    def test_contains_key_name(self):
        r = PauseReporter([_make_result("my_pipe")])
        assert "my_pipe" in r.format_text()

    def test_paused_label_present(self):
        r = PauseReporter([_make_result(paused=True)])
        assert "PAUSED" in r.format_text()

    def test_active_label_present(self):
        r = PauseReporter([_make_result(paused=False)])
        assert "ACTIVE" in r.format_text()

    def test_auto_resumed_label_present(self):
        r = PauseReporter([_make_result(paused=False, auto_resumed=True)])
        assert "auto-resumed" in r.format_text()

    def test_has_paused_true(self):
        r = PauseReporter([_make_result(paused=True)])
        assert r.has_paused() is True

    def test_has_paused_false(self):
        r = PauseReporter([_make_result(paused=False)])
        assert r.has_paused() is False

    def test_has_auto_resumed(self):
        r = PauseReporter([_make_result(paused=False, auto_resumed=True)])
        assert r.has_auto_resumed() is True

    def test_paused_results_filters_correctly(self):
        results = [_make_result("a", paused=True), _make_result("b", paused=False)]
        r = PauseReporter(results)
        assert len(r.paused_results()) == 1
        assert r.paused_results()[0].key == "a"

    def test_format_json_returns_list(self):
        r = PauseReporter([_make_result()])
        data = r.format_json()
        assert isinstance(data, list)
        assert data[0]["key"] == "pipe_a"
