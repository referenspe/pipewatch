"""Tests for pipewatch.sla."""
import pytest
from datetime import datetime, timedelta

from pipewatch.sla import SLAConfig, SLABreachEvent, SLATracker


NOW = datetime(2024, 6, 1, 12, 0, 0)


def _tracker(target: float = 99.9, max_breach: int = 5, window_hours: int = 24) -> SLATracker:
    config = SLAConfig(
        target_availability=target,
        max_breach_minutes=max_breach,
        window_hours=window_hours,
    )
    return SLATracker(config)


class TestSLAConfig:
    def test_defaults(self):
        cfg = SLAConfig()
        assert cfg.target_availability == 99.9
        assert cfg.max_breach_minutes == 5
        assert cfg.window_hours == 24

    def test_from_dict_custom(self):
        cfg = SLAConfig.from_dict({"target_availability": 95.0, "window_hours": 12})
        assert cfg.target_availability == 95.0
        assert cfg.window_hours == 12

    def test_from_dict_defaults_when_missing(self):
        cfg = SLAConfig.from_dict({})
        assert cfg.target_availability == 99.9

    def test_to_dict_round_trip(self):
        cfg = SLAConfig(target_availability=98.0, max_breach_minutes=10, window_hours=6)
        assert SLAConfig.from_dict(cfg.to_dict()).target_availability == 98.0


class TestSLABreachEvent:
    def test_duration_minutes_closed(self):
        start = NOW - timedelta(minutes=30)
        event = SLABreachEvent(metric_key="cpu", started_at=start, ended_at=NOW)
        assert abs(event.duration_minutes - 30.0) < 0.01

    def test_duration_minutes_open_uses_utcnow(self):
        start = datetime.utcnow() - timedelta(minutes=5)
        event = SLABreachEvent(metric_key="cpu", started_at=start)
        assert event.duration_minutes >= 4.9

    def test_to_dict_contains_key(self):
        event = SLABreachEvent(metric_key="lag", started_at=NOW, ended_at=NOW)
        d = event.to_dict()
        assert d["metric_key"] == "lag"
        assert d["duration_minutes"] == 0.0


class TestSLATrackerEvaluate:
    def test_no_breaches_is_fully_available(self):
        tracker = _tracker()
        result = tracker.evaluate("throughput", now=NOW)
        assert result.availability_pct == pytest.approx(100.0)
        assert result.compliant is True

    def test_breach_reduces_availability(self):
        tracker = _tracker(target=99.9, window_hours=24)
        start = NOW - timedelta(minutes=60)
        tracker.record_breach("cpu", started_at=start, ended_at=NOW)
        result = tracker.evaluate("cpu", now=NOW)
        # 60 breached out of 1440 minutes => ~95.8% availability
        assert result.availability_pct < 99.9
        assert result.compliant is False

    def test_small_breach_within_target_is_compliant(self):
        tracker = _tracker(target=95.0, window_hours=24)
        start = NOW - timedelta(minutes=10)
        tracker.record_breach("lag", started_at=start, ended_at=NOW)
        result = tracker.evaluate("lag", now=NOW)
        assert result.compliant is True

    def test_breach_outside_window_is_ignored(self):
        tracker = _tracker(window_hours=1)
        old_start = NOW - timedelta(hours=3)
        old_end = NOW - timedelta(hours=2)
        tracker.record_breach("cpu", started_at=old_start, ended_at=old_end)
        result = tracker.evaluate("cpu", now=NOW)
        assert result.availability_pct == pytest.approx(100.0)

    def test_evaluate_all_returns_all_keys(self):
        tracker = _tracker()
        tracker.record_breach("a", started_at=NOW - timedelta(minutes=1), ended_at=NOW)
        tracker.record_breach("b", started_at=NOW - timedelta(minutes=2), ended_at=NOW)
        results = tracker.evaluate_all(now=NOW)
        keys = {r.metric_key for r in results}
        assert keys == {"a", "b"}

    def test_result_to_dict_has_expected_fields(self):
        tracker = _tracker()
        tracker.record_breach("x", started_at=NOW - timedelta(minutes=5), ended_at=NOW)
        d = tracker.evaluate("x", now=NOW).to_dict()
        assert "availability_pct" in d
        assert "compliant" in d
        assert "breach_count" in d
        assert d["breach_count"] == 1
