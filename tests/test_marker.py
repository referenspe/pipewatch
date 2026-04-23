"""Tests for pipewatch.marker and pipewatch.marker_reporter."""
import json
import pytest

from pipewatch.marker import Marker, MarkerConfig, MarkerEvent, MarkerResult
from pipewatch.marker_reporter import MarkerReporter


# ---------------------------------------------------------------------------
# MarkerConfig
# ---------------------------------------------------------------------------

class TestMarkerConfig:
    def test_defaults(self):
        cfg = MarkerConfig()
        assert cfg.max_markers == 100
        assert cfg.track_counts is True

    def test_from_dict_custom(self):
        cfg = MarkerConfig.from_dict({"max_markers": 10, "track_counts": False})
        assert cfg.max_markers == 10
        assert cfg.track_counts is False

    def test_from_dict_defaults_when_missing(self):
        cfg = MarkerConfig.from_dict({})
        assert cfg.max_markers == 100

    def test_to_dict_round_trip(self):
        cfg = MarkerConfig(max_markers=50, track_counts=False)
        assert MarkerConfig.from_dict(cfg.to_dict()).max_markers == 50


# ---------------------------------------------------------------------------
# Marker
# ---------------------------------------------------------------------------

class TestMarker:
    def test_mark_creates_event(self):
        m = Marker()
        event = m.mark("etl.start", "ETL started")
        assert event is not None
        assert event.key == "etl.start"
        assert event.label == "ETL started"

    def test_mark_increments_count(self):
        m = Marker()
        m.mark("etl.start", "ETL started")
        event = m.mark("etl.start", "ETL started")
        assert event.count == 2

    def test_mark_no_count_when_disabled(self):
        m = Marker(config=MarkerConfig(track_counts=False))
        m.mark("k", "label")
        event = m.mark("k", "label")
        assert event.count == 0

    def test_max_markers_respected(self):
        m = Marker(config=MarkerConfig(max_markers=2))
        m.mark("a", "A")
        m.mark("b", "B")
        result = m.mark("c", "C")
        assert result is None
        assert m.get("c") is None

    def test_get_returns_none_for_unknown(self):
        m = Marker()
        assert m.get("missing") is None

    def test_reset_removes_key(self):
        m = Marker()
        m.mark("x", "X")
        m.reset("x")
        assert m.get("x") is None

    def test_clear_removes_all(self):
        m = Marker()
        m.mark("a", "A")
        m.mark("b", "B")
        m.clear()
        assert m.report().events == []

    def test_report_contains_all_events(self):
        m = Marker()
        m.mark("p", "P")
        m.mark("q", "Q")
        result = m.report()
        keys = {e.key for e in result.events}
        assert keys == {"p", "q"}


# ---------------------------------------------------------------------------
# MarkerReporter
# ---------------------------------------------------------------------------

class TestMarkerReporter:
    def _reporter(self, *pairs):
        events = [MarkerEvent(key=k, label=l, count=c) for k, l, c in pairs]
        return MarkerReporter(MarkerResult(events=events))

    def test_empty_results_message(self):
        r = MarkerReporter(MarkerResult())
        assert "No markers" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert MarkerReporter(MarkerResult()).has_results is False

    def test_has_results_true_when_populated(self):
        r = self._reporter(("k", "L", 1))
        assert r.has_results is True

    def test_total_marks(self):
        r = self._reporter(("a", "A", 3), ("b", "B", 7))
        assert r.total_marks == 10

    def test_top_returns_sorted_by_count(self):
        r = self._reporter(("a", "A", 1), ("b", "B", 5), ("c", "C", 3))
        top = r.top(2)
        assert top[0].key == "b"
        assert top[1].key == "c"

    def test_format_text_contains_key(self):
        r = self._reporter(("etl.done", "Done", 2))
        assert "etl.done" in r.format_text()

    def test_format_json_valid(self):
        r = self._reporter(("x", "X", 1))
        data = json.loads(r.format_json())
        assert "events" in data
        assert data["events"][0]["key"] == "x"
