"""Tests for pipewatch.fanout."""
from __future__ import annotations

import pytest

from pipewatch.fanout import Fanout, FanoutConfig, FanoutResult


# ---------------------------------------------------------------------------
# FanoutConfig
# ---------------------------------------------------------------------------

class TestFanoutConfig:
    def test_defaults(self):
        cfg = FanoutConfig()
        assert cfg.channels == []
        assert cfg.stop_on_error is False
        assert cfg.max_channels == 16

    def test_from_dict_custom(self):
        cfg = FanoutConfig.from_dict(
            {"channels": ["slack", "email"], "stop_on_error": True, "max_channels": 4}
        )
        assert cfg.channels == ["slack", "email"]
        assert cfg.stop_on_error is True
        assert cfg.max_channels == 4

    def test_from_dict_defaults_when_missing(self):
        cfg = FanoutConfig.from_dict({})
        assert cfg.channels == []
        assert cfg.stop_on_error is False

    def test_to_dict_round_trip(self):
        cfg = FanoutConfig(channels=["a"], stop_on_error=True, max_channels=8)
        assert FanoutConfig.from_dict(cfg.to_dict()).channels == ["a"]

    def test_raises_if_max_channels_zero(self):
        with pytest.raises(ValueError, match="max_channels"):
            FanoutConfig(max_channels=0)

    def test_raises_if_channels_exceed_max(self):
        with pytest.raises(ValueError, match="exceeds max_channels"):
            FanoutConfig(channels=["a", "b", "c"], max_channels=2)


# ---------------------------------------------------------------------------
# Fanout.register
# ---------------------------------------------------------------------------

class TestFanoutRegister:
    def test_register_stores_handler(self):
        f = Fanout()
        f.register("ch", lambda p: None)
        assert "ch" in f._handlers

    def test_register_raises_when_max_reached(self):
        f = Fanout(FanoutConfig(max_channels=1))
        f.register("first", lambda p: None)
        with pytest.raises(RuntimeError, match="max_channels"):
            f.register("second", lambda p: None)


# ---------------------------------------------------------------------------
# Fanout.dispatch
# ---------------------------------------------------------------------------

class TestFanoutDispatch:
    def _make_fanout(self, channels=None, stop_on_error=False):
        cfg = FanoutConfig(channels=channels or [], stop_on_error=stop_on_error)
        return Fanout(cfg)

    def test_dispatches_to_all_registered(self):
        received = []
        f = self._make_fanout()
        f.register("a", lambda p: received.append(("a", p)))
        f.register("b", lambda p: received.append(("b", p)))
        result = f.dispatch("my_metric", {"value": 1})
        assert result.total_sent == 2
        assert not result.has_failures
        assert len(received) == 2

    def test_missing_handler_recorded_as_failure(self):
        f = Fanout(FanoutConfig(channels=["missing"]))
        result = f.dispatch("k", {})
        assert result.has_failures
        assert "missing" in result.failed

    def test_exception_in_handler_recorded(self):
        f = self._make_fanout()
        f.register("bad", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
        result = f.dispatch("k", {})
        assert "bad" in result.failed
        assert "boom" in result.failed["bad"]

    def test_stop_on_error_halts_dispatch(self):
        called = []
        f = Fanout(FanoutConfig(channels=["bad", "good"], stop_on_error=True))
        f.register("bad", lambda p: (_ for _ in ()).throw(RuntimeError("err")))
        f.register("good", lambda p: called.append("good"))
        f.dispatch("k", {})
        assert "good" not in called

    def test_continues_after_error_without_stop_flag(self):
        called = []
        f = Fanout(FanoutConfig(channels=["bad", "good"], stop_on_error=False))
        f.register("bad", lambda p: (_ for _ in ()).throw(RuntimeError("err")))
        f.register("good", lambda p: called.append("good"))
        f.dispatch("k", {})
        assert "good" in called

    def test_result_metric_key_set(self):
        f = self._make_fanout()
        result = f.dispatch("pipeline.errors", {})
        assert result.metric_key == "pipeline.errors"
