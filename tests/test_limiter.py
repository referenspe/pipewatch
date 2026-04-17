"""Tests for pipewatch.limiter and pipewatch.limiter_reporter."""
import pytest
from pipewatch.limiter import LimiterConfig, Limiter
from pipewatch.limiter_reporter import LimiterReporter


class TestLimiterConfig:
    def test_defaults(self):
        cfg = LimiterConfig()
        assert cfg.max_events == 10
        assert cfg.window_seconds == 60.0

    def test_from_dict_custom(self):
        cfg = LimiterConfig.from_dict({"max_events": 5, "window_seconds": 30.0})
        assert cfg.max_events == 5
        assert cfg.window_seconds == 30.0

    def test_from_dict_defaults_when_missing(self):
        cfg = LimiterConfig.from_dict({})
        assert cfg.max_events == 10

    def test_to_dict_round_trip(self):
        cfg = LimiterConfig(max_events=3, window_seconds=15.0)
        assert LimiterConfig.from_dict(cfg.to_dict()).max_events == 3


class TestLimiter:
    def test_allows_under_limit(self):
        lim = Limiter(LimiterConfig(max_events=3, window_seconds=60.0))
        result = lim.check("k", now=0.0)
        assert result.allowed is True

    def test_blocks_at_limit(self):
        lim = Limiter(LimiterConfig(max_events=2, window_seconds=60.0))
        lim.check("k", now=0.0)
        lim.check("k", now=1.0)
        result = lim.check("k", now=2.0)
        assert result.allowed is False

    def test_allows_after_window_expires(self):
        lim = Limiter(LimiterConfig(max_events=1, window_seconds=10.0))
        lim.check("k", now=0.0)
        result = lim.check("k", now=11.0)
        assert result.allowed is True

    def test_current_count_reflects_window(self):
        lim = Limiter(LimiterConfig(max_events=5, window_seconds=10.0))
        lim.check("k", now=0.0)
        lim.check("k", now=1.0)
        result = lim.check("k", now=2.0)
        assert result.current_count == 3

    def test_reset_clears_key(self):
        lim = Limiter(LimiterConfig(max_events=1, window_seconds=60.0))
        lim.check("k", now=0.0)
        lim.reset("k")
        result = lim.check("k", now=1.0)
        assert result.allowed is True

    def test_reset_all_clears_everything(self):
        lim = Limiter(LimiterConfig(max_events=1, window_seconds=60.0))
        lim.check("a", now=0.0)
        lim.check("b", now=0.0)
        lim.reset_all()
        assert lim.check("a", now=1.0).allowed is True
        assert lim.check("b", now=1.0).allowed is True

    def test_independent_keys(self):
        lim = Limiter(LimiterConfig(max_events=1, window_seconds=60.0))
        lim.check("a", now=0.0)
        result_b = lim.check("b", now=0.0)
        assert result_b.allowed is True


class TestLimiterReporter:
    def _make_results(self):
        lim = Limiter(LimiterConfig(max_events=1, window_seconds=60.0))
        r1 = lim.check("pipe_a", now=0.0)
        r2 = lim.check("pipe_a", now=1.0)
        return [r1, r2]

    def test_has_throttled_true(self):
        reporter = LimiterReporter(self._make_results())
        assert reporter.has_throttled() is True

    def test_throttled_results_filters_correctly(self):
        reporter = LimiterReporter(self._make_results())
        assert all(not r.allowed for r in reporter.throttled_results())

    def test_format_text_contains_key(self):
        reporter = LimiterReporter(self._make_results())
        assert "pipe_a" in reporter.format_text()

    def test_format_text_empty(self):
        reporter = LimiterReporter([])
        assert "no results" in reporter.format_text()

    def test_format_json_parses(self):
        import json
        reporter = LimiterReporter(self._make_results())
        data = json.loads(reporter.format_json())
        assert isinstance(data, list)
        assert data[0]["key"] == "pipe_a"
