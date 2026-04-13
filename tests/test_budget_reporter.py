"""Tests for pipewatch.budget_reporter."""
import json

import pytest

from pipewatch.budget import AlertBudget, BudgetConfig
from pipewatch.budget_reporter import BudgetReporter


def _reporter(max_alerts=5, per_key=False):
    budget = AlertBudget(BudgetConfig(max_alerts=max_alerts, per_key=per_key))
    return budget, BudgetReporter(budget)


class TestBudgetReporterText:
    def test_empty_keys_message(self):
        _, reporter = _reporter()
        out = reporter.format_text([])
        assert "no keys" in out.lower()

    def test_contains_key_name(self):
        budget, reporter = _reporter(per_key=True)
        budget.consume("cpu")
        out = reporter.format_text(["cpu"])
        assert "cpu" in out

    def test_ok_label_when_under_limit(self):
        _, reporter = _reporter(max_alerts=10)
        out = reporter.format_text(["cpu"])
        assert "OK" in out

    def test_exhausted_label_when_over_limit(self):
        budget, reporter = _reporter(max_alerts=1)
        budget.consume("cpu")
        budget.consume("cpu")
        out = reporter.format_text(["cpu"])
        assert "EXHAUSTED" in out

    def test_shows_used_and_limit(self):
        budget, reporter = _reporter(max_alerts=5)
        budget.consume("cpu")
        out = reporter.format_text(["cpu"])
        assert "/5" in out


class TestBudgetReporterJson:
    def test_returns_valid_json(self):
        _, reporter = _reporter()
        raw = reporter.format_json(["cpu"])
        parsed = json.loads(raw)
        assert isinstance(parsed, list)

    def test_json_contains_allowed_field(self):
        _, reporter = _reporter()
        parsed = json.loads(reporter.format_json(["cpu"]))
        assert "allowed" in parsed[0]

    def test_json_empty_list_for_no_keys(self):
        _, reporter = _reporter()
        parsed = json.loads(reporter.format_json([]))
        assert parsed == []


class TestBudgetReporterHasExhausted:
    def test_false_when_all_ok(self):
        _, reporter = _reporter(max_alerts=10)
        assert reporter.has_exhausted(["cpu", "memory"]) is False

    def test_true_when_any_exhausted(self):
        budget, reporter = _reporter(max_alerts=1)
        budget.consume("cpu")
        budget.consume("cpu")
        assert reporter.has_exhausted(["cpu"]) is True
