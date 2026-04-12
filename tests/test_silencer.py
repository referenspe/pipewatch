"""Tests for pipewatch.silencer."""

import time
import pytest

from pipewatch.silencer import SilenceRule, Silencer


# ---------------------------------------------------------------------------
# SilenceRule
# ---------------------------------------------------------------------------

class TestSilenceRule:
    def test_active_before_expiry(self):
        rule = SilenceRule(metric_key="cpu", expires_at=time.time() + 60)
        assert rule.is_active() is True

    def test_inactive_after_expiry(self):
        rule = SilenceRule(metric_key="cpu", expires_at=time.time() - 1)
        assert rule.is_active() is False

    def test_active_uses_provided_now(self):
        rule = SilenceRule(metric_key="cpu", expires_at=1000.0)
        assert rule.is_active(now=999.0) is True
        assert rule.is_active(now=1001.0) is False

    def test_to_dict_round_trip(self):
        rule = SilenceRule(metric_key="lag", expires_at=5000.0, reason="deploy")
        restored = SilenceRule.from_dict(rule.to_dict())
        assert restored.metric_key == rule.metric_key
        assert restored.expires_at == rule.expires_at
        assert restored.reason == rule.reason

    def test_from_dict_default_reason(self):
        data = {"metric_key": "mem", "expires_at": 9999.0}
        rule = SilenceRule.from_dict(data)
        assert rule.reason == ""


# ---------------------------------------------------------------------------
# Silencer
# ---------------------------------------------------------------------------

class TestSilencer:
    def test_silence_returns_rule(self):
        s = Silencer()
        rule = s.silence("cpu", 60, reason="maintenance")
        assert isinstance(rule, SilenceRule)
        assert rule.metric_key == "cpu"
        assert rule.reason == "maintenance"

    def test_is_silenced_true_when_active(self):
        s = Silencer()
        s.silence("cpu", 120)
        assert s.is_silenced("cpu") is True

    def test_is_silenced_false_for_unknown_key(self):
        s = Silencer()
        assert s.is_silenced("unknown") is False

    def test_is_silenced_false_after_expiry(self):
        s = Silencer()
        s.silence("cpu", 60)
        future = time.time() + 120
        assert s.is_silenced("cpu", now=future) is False

    def test_raises_on_non_positive_duration(self):
        s = Silencer()
        with pytest.raises(ValueError):
            s.silence("cpu", 0)
        with pytest.raises(ValueError):
            s.silence("cpu", -5)

    def test_prune_removes_expired_rules(self):
        s = Silencer()
        past = time.time() - 10
        s._rules["cpu"] = [SilenceRule("cpu", past)]
        removed = s.prune()
        assert removed == 1
        assert "cpu" not in s._rules

    def test_prune_keeps_active_rules(self):
        s = Silencer()
        s.silence("mem", 300)
        removed = s.prune()
        assert removed == 0
        assert s.is_silenced("mem") is True

    def test_active_rules_returns_only_active(self):
        s = Silencer()
        now = time.time()
        s._rules["cpu"] = [
            SilenceRule("cpu", now + 60),
            SilenceRule("cpu", now - 1),
        ]
        active = s.active_rules(now=now)
        assert len(active) == 1
        assert active[0].metric_key == "cpu"

    def test_multiple_keys_tracked_independently(self):
        s = Silencer()
        s.silence("cpu", 60)
        s.silence("lag", 60)
        assert s.is_silenced("cpu") is True
        assert s.is_silenced("lag") is True
        assert s.is_silenced("mem") is False
