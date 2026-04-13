"""Tests for pipewatch.quota and pipewatch.quota_reporter."""
import json
from datetime import datetime, timedelta

import pytest

from pipewatch.quota import QuotaConfig, QuotaEnforcer
from pipewatch.quota_reporter import QuotaReporter


# ---------------------------------------------------------------------------
# QuotaConfig
# ---------------------------------------------------------------------------

class TestQuotaConfig:
    def test_defaults(self):
        cfg = QuotaConfig()
        assert cfg.window_seconds == 60
        assert cfg.max_events == 100

    def test_from_dict_custom(self):
        cfg = QuotaConfig.from_dict({"window_seconds": 30, "max_events": 10})
        assert cfg.window_seconds == 30
        assert cfg.max_events == 10

    def test_from_dict_defaults_when_missing(self):
        cfg = QuotaConfig.from_dict({})
        assert cfg.window_seconds == 60

    def test_to_dict_round_trip(self):
        cfg = QuotaConfig(window_seconds=45, max_events=20)
        assert QuotaConfig.from_dict(cfg.to_dict()).max_events == 20

    def test_raises_if_window_not_positive(self):
        with pytest.raises(ValueError):
            QuotaConfig(window_seconds=0)

    def test_raises_if_max_events_less_than_one(self):
        with pytest.raises(ValueError):
            QuotaConfig(max_events=0)


# ---------------------------------------------------------------------------
# QuotaEnforcer
# ---------------------------------------------------------------------------

class TestQuotaEnforcer:
    def _now(self):
        return datetime(2024, 1, 1, 12, 0, 0)

    def test_first_event_allowed(self):
        enforcer = QuotaEnforcer(QuotaConfig(max_events=5, window_seconds=60))
        result = enforcer.check("pipe_a", now=self._now())
        assert result.allowed is True
        assert result.current_count == 1

    def test_blocks_when_limit_reached(self):
        enforcer = QuotaEnforcer(QuotaConfig(max_events=3, window_seconds=60))
        now = self._now()
        for _ in range(3):
            enforcer.check("pipe_a", now=now)
        result = enforcer.check("pipe_a", now=now)
        assert result.allowed is False
        assert result.current_count == 3

    def test_window_expiry_allows_new_events(self):
        enforcer = QuotaEnforcer(QuotaConfig(max_events=2, window_seconds=10))
        t0 = self._now()
        enforcer.check("pipe_a", now=t0)
        enforcer.check("pipe_a", now=t0)
        # Advance past the window
        t1 = t0 + timedelta(seconds=11)
        result = enforcer.check("pipe_a", now=t1)
        assert result.allowed is True

    def test_reset_clears_state(self):
        enforcer = QuotaEnforcer(QuotaConfig(max_events=1, window_seconds=60))
        now = self._now()
        enforcer.check("pipe_a", now=now)
        enforcer.reset("pipe_a")
        assert enforcer.usage("pipe_a", now=now) == 0

    def test_usage_returns_zero_for_unknown_key(self):
        enforcer = QuotaEnforcer()
        assert enforcer.usage("unknown") == 0

    def test_keys_are_independent(self):
        enforcer = QuotaEnforcer(QuotaConfig(max_events=1, window_seconds=60))
        now = self._now()
        enforcer.check("key_a", now=now)
        result = enforcer.check("key_b", now=now)
        assert result.allowed is True


# ---------------------------------------------------------------------------
# QuotaReporter
# ---------------------------------------------------------------------------

class TestQuotaReporter:
    def _make_result(self, key="pipe", allowed=True, count=5, limit=10, window=60):
        from pipewatch.quota import QuotaResult
        return QuotaResult(key=key, allowed=allowed, current_count=count,
                           limit=limit, window_seconds=window)

    def test_empty_results_message(self):
        reporter = QuotaReporter([])
        assert "no results" in reporter.format_text()

    def test_has_violations_false_when_all_allowed(self):
        reporter = QuotaReporter([self._make_result(allowed=True)])
        assert reporter.has_violations() is False

    def test_has_violations_true_when_any_blocked(self):
        reporter = QuotaReporter([self._make_result(allowed=False)])
        assert reporter.has_violations() is True

    def test_format_text_contains_key(self):
        reporter = QuotaReporter([self._make_result(key="my_pipe")])
        assert "my_pipe" in reporter.format_text()

    def test_format_text_shows_blocked(self):
        reporter = QuotaReporter([self._make_result(allowed=False)])
        assert "BLOCKED" in reporter.format_text()

    def test_format_json_structure(self):
        reporter = QuotaReporter([self._make_result(allowed=False)])
        data = json.loads(reporter.format_json())
        assert data["quota_violations"] is True
        assert len(data["results"]) == 1
