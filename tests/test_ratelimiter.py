"""Tests for pipewatch.ratelimiter."""

from datetime import datetime, timedelta, timezone

import pytest

from pipewatch.ratelimiter import RateLimiter, RateLimiterConfig


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# RateLimiterConfig
# ---------------------------------------------------------------------------

class TestRateLimiterConfig:
    def test_defaults(self):
        cfg = RateLimiterConfig()
        assert cfg.min_interval_seconds == 60.0
        assert cfg.max_per_minute == 10

    def test_raises_if_interval_not_positive(self):
        with pytest.raises(ValueError, match="min_interval_seconds"):
            RateLimiterConfig(min_interval_seconds=0)

    def test_raises_if_max_per_minute_less_than_one(self):
        with pytest.raises(ValueError, match="max_per_minute"):
            RateLimiterConfig(max_per_minute=0)

    def test_from_dict_custom(self):
        cfg = RateLimiterConfig.from_dict({"min_interval_seconds": 30, "max_per_minute": 5})
        assert cfg.min_interval_seconds == 30.0
        assert cfg.max_per_minute == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = RateLimiterConfig.from_dict({})
        assert cfg.min_interval_seconds == 60.0
        assert cfg.max_per_minute == 10

    def test_to_dict_round_trip(self):
        cfg = RateLimiterConfig(min_interval_seconds=45.0, max_per_minute=3)
        assert RateLimiterConfig.from_dict(cfg.to_dict()).min_interval_seconds == 45.0


# ---------------------------------------------------------------------------
# RateLimiter.check — min_interval
# ---------------------------------------------------------------------------

class TestRateLimiterMinInterval:
    def test_first_call_is_allowed(self):
        rl = RateLimiter(RateLimiterConfig(min_interval_seconds=60))
        result = rl.check("cpu", now=NOW)
        assert result.allowed is True
        assert result.reason == "ok"

    def test_second_call_within_interval_blocked(self):
        rl = RateLimiter(RateLimiterConfig(min_interval_seconds=60))
        rl.check("cpu", now=NOW)
        result = rl.check("cpu", now=NOW + timedelta(seconds=30))
        assert result.allowed is False
        assert result.reason == "min_interval"

    def test_second_call_after_interval_allowed(self):
        rl = RateLimiter(RateLimiterConfig(min_interval_seconds=60))
        rl.check("cpu", now=NOW)
        result = rl.check("cpu", now=NOW + timedelta(seconds=61))
        assert result.allowed is True

    def test_different_keys_are_independent(self):
        rl = RateLimiter(RateLimiterConfig(min_interval_seconds=60))
        rl.check("cpu", now=NOW)
        result = rl.check("mem", now=NOW)
        assert result.allowed is True


# ---------------------------------------------------------------------------
# RateLimiter.check — max_per_minute
# ---------------------------------------------------------------------------

class TestRateLimiterMaxPerMinute:
    def test_exceeding_max_blocks(self):
        rl = RateLimiter(RateLimiterConfig(min_interval_seconds=1, max_per_minute=3))
        for i in range(3):
            r = rl.check("k", now=NOW + timedelta(seconds=i))
            assert r.allowed is True
        result = rl.check("k", now=NOW + timedelta(seconds=3))
        assert result.allowed is False
        assert result.reason == "max_per_minute"

    def test_window_resets_after_sixty_seconds(self):
        rl = RateLimiter(RateLimiterConfig(min_interval_seconds=1, max_per_minute=2))
        rl.check("k", now=NOW)
        rl.check("k", now=NOW + timedelta(seconds=1))
        # window exhausted
        assert rl.check("k", now=NOW + timedelta(seconds=2)).allowed is False
        # new window
        result = rl.check("k", now=NOW + timedelta(seconds=61))
        assert result.allowed is True


# ---------------------------------------------------------------------------
# RateLimiter.reset
# ---------------------------------------------------------------------------

def test_reset_clears_state():
    rl = RateLimiter(RateLimiterConfig(min_interval_seconds=60))
    rl.check("cpu", now=NOW)
    rl.reset("cpu")
    result = rl.check("cpu", now=NOW + timedelta(seconds=5))
    assert result.allowed is True
