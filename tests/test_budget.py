"""Tests for pipewatch.budget."""
from datetime import datetime, timedelta

import pytest

from pipewatch.budget import AlertBudget, BudgetConfig


class TestBudgetConfig:
    def test_defaults(self):
        cfg = BudgetConfig()
        assert cfg.max_alerts == 20
        assert cfg.window_seconds == 3600
        assert cfg.per_key is False

    def test_from_dict_custom(self):
        cfg = BudgetConfig.from_dict({"max_alerts": 5, "window_seconds": 60, "per_key": True})
        assert cfg.max_alerts == 5
        assert cfg.window_seconds == 60
        assert cfg.per_key is True

    def test_from_dict_defaults_when_missing(self):
        cfg = BudgetConfig.from_dict({})
        assert cfg.max_alerts == 20

    def test_to_dict_round_trip(self):
        cfg = BudgetConfig(max_alerts=3, window_seconds=120, per_key=True)
        assert BudgetConfig.from_dict(cfg.to_dict()) == cfg


class TestAlertBudgetGlobal:
    def _budget(self, max_alerts=3, window_seconds=60):
        return AlertBudget(BudgetConfig(max_alerts=max_alerts, window_seconds=window_seconds))

    def test_first_alert_allowed(self):
        b = self._budget()
        result = b.consume("cpu")
        assert result.allowed is True
        assert result.used == 0  # used *before* this consume

    def test_exhausted_after_limit(self):
        b = self._budget(max_alerts=2)
        b.consume("cpu")
        b.consume("cpu")
        result = b.consume("cpu")
        assert result.allowed is False

    def test_check_does_not_consume(self):
        b = self._budget(max_alerts=1)
        b.check("cpu")
        b.check("cpu")
        result = b.consume("cpu")
        assert result.allowed is True

    def test_old_alerts_pruned(self):
        b = self._budget(max_alerts=2, window_seconds=10)
        past = datetime.utcnow() - timedelta(seconds=20)
        b.consume("cpu", now=past)
        b.consume("cpu", now=past)
        # Window has passed; both slots should be free
        result = b.consume("cpu")
        assert result.allowed is True

    def test_reset_clears_all(self):
        b = self._budget(max_alerts=1)
        b.consume("cpu")
        b.reset()
        result = b.consume("cpu")
        assert result.allowed is True

    def test_result_to_dict_keys(self):
        b = self._budget()
        r = b.check("cpu")
        d = r.to_dict()
        assert set(d.keys()) == {"allowed", "key", "used", "limit", "window_seconds"}


class TestAlertBudgetPerKey:
    def _budget(self, max_alerts=2):
        return AlertBudget(BudgetConfig(max_alerts=max_alerts, per_key=True))

    def test_keys_tracked_independently(self):
        b = self._budget(max_alerts=1)
        b.consume("cpu")
        result = b.consume("memory")
        assert result.allowed is True

    def test_same_key_exhausted_independently(self):
        b = self._budget(max_alerts=1)
        b.consume("cpu")
        result = b.consume("cpu")
        assert result.allowed is False

    def test_reset_specific_key(self):
        b = self._budget(max_alerts=1)
        b.consume("cpu")
        b.reset("cpu")
        assert b.consume("cpu").allowed is True
