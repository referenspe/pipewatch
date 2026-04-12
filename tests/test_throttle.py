"""Tests for pipewatch.throttle."""
import pytest
from pipewatch.throttle import AlertThrottler, ThrottleConfig


class TestThrottleConfig:
    def test_defaults(self):
        cfg = ThrottleConfig()
        assert cfg.window_seconds == 300.0
        assert cfg.max_alerts_per_window == 3

    def test_from_dict_custom(self):
        cfg = ThrottleConfig.from_dict({"window_seconds": 60, "max_alerts_per_window": 1})
        assert cfg.window_seconds == 60.0
        assert cfg.max_alerts_per_window == 1

    def test_from_dict_defaults_when_missing(self):
        cfg = ThrottleConfig.from_dict({})
        assert cfg.window_seconds == 300.0
        assert cfg.max_alerts_per_window == 3

    def test_to_dict_round_trip(self):
        cfg = ThrottleConfig(window_seconds=120.0, max_alerts_per_window=5)
        assert ThrottleConfig.from_dict(cfg.to_dict()) == cfg


class TestAlertThrottler:
    def _throttler(self, max_alerts=2, window=100.0):
        return AlertThrottler(ThrottleConfig(window_seconds=window, max_alerts_per_window=max_alerts))

    def test_first_alert_always_sent(self):
        t = self._throttler()
        assert t.should_send("cpu", now=0.0) is True

    def test_allows_up_to_max_alerts(self):
        t = self._throttler(max_alerts=3)
        for _ in range(3):
            assert t.should_send("cpu", now=0.0) is True

    def test_suppresses_beyond_max(self):
        t = self._throttler(max_alerts=2)
        t.should_send("cpu", now=0.0)
        t.should_send("cpu", now=1.0)
        assert t.should_send("cpu", now=2.0) is False

    def test_different_keys_tracked_independently(self):
        t = self._throttler(max_alerts=1)
        assert t.should_send("cpu", now=0.0) is True
        assert t.should_send("mem", now=0.0) is True
        assert t.should_send("cpu", now=1.0) is False
        assert t.should_send("mem", now=1.0) is False

    def test_window_expiry_allows_new_alerts(self):
        t = self._throttler(max_alerts=1, window=10.0)
        assert t.should_send("cpu", now=0.0) is True
        assert t.should_send("cpu", now=5.0) is False
        # After window expires the old entry is pruned
        assert t.should_send("cpu", now=11.0) is True

    def test_reset_clears_window(self):
        t = self._throttler(max_alerts=1)
        t.should_send("cpu", now=0.0)
        t.reset("cpu")
        assert t.should_send("cpu", now=1.0) is True

    def test_reset_unknown_key_is_safe(self):
        t = self._throttler()
        t.reset("nonexistent")  # should not raise

    def test_stats_returns_correct_count(self):
        t = self._throttler(max_alerts=5, window=100.0)
        t.should_send("cpu", now=0.0)
        t.should_send("cpu", now=1.0)
        stats = t.stats("cpu", now=2.0)
        assert stats["alerts_in_window"] == 2
        assert stats["metric_key"] == "cpu"
        assert stats["max_alerts_per_window"] == 5
        assert stats["window_seconds"] == 100.0

    def test_stats_prunes_expired(self):
        t = self._throttler(max_alerts=5, window=10.0)
        t.should_send("cpu", now=0.0)
        t.should_send("cpu", now=1.0)
        stats = t.stats("cpu", now=15.0)  # both entries expired
        assert stats["alerts_in_window"] == 0
