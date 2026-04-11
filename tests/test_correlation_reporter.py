"""Tests for pipewatch.correlation_reporter."""
from __future__ import annotations

import json

from pipewatch.correlation import CorrelationResult, CorrelationStrength
from pipewatch.correlation_reporter import CorrelationReporter


def _make_result(
    key_a: str = "cpu",
    key_b: str = "memory",
    coefficient: float = 0.82,
    strength: CorrelationStrength = CorrelationStrength.STRONG,
    sample_count: int = 20,
) -> CorrelationResult:
    return CorrelationResult(
        key_a=key_a,
        key_b=key_b,
        coefficient=coefficient,
        strength=strength,
        sample_count=sample_count,
    )


class TestCorrelationReporterText:
    def test_empty_results_message(self):
        reporter = CorrelationReporter([])
        assert "No correlation" in reporter.format_text()

    def test_contains_metric_keys(self):
        r = _make_result(key_a="cpu", key_b="memory")
        text = CorrelationReporter([r]).format_text()
        assert "cpu" in text
        assert "memory" in text

    def test_contains_coefficient(self):
        r = _make_result(coefficient=0.82)
        text = CorrelationReporter([r]).format_text()
        assert "0.8200" in text

    def test_contains_strength_label(self):
        r = _make_result(strength=CorrelationStrength.MODERATE, coefficient=0.55)
        text = CorrelationReporter([r]).format_text()
        assert "moderate" in text

    def test_negative_coefficient_no_plus_sign(self):
        r = _make_result(coefficient=-0.75)
        text = CorrelationReporter([r]).format_text()
        assert "-0.7500" in text
        assert "r=+-" not in text

    def test_contains_sample_count(self):
        r = _make_result(sample_count=15)
        text = CorrelationReporter([r]).format_text()
        assert "n=15" in text


class TestCorrelationReporterJson:
    def test_empty_returns_empty_list(self):
        payload = json.loads(CorrelationReporter([]).format_json())
        assert payload == []

    def test_json_contains_keys(self):
        r = _make_result()
        payload = json.loads(CorrelationReporter([r]).format_json())
        assert len(payload) == 1
        assert payload[0]["key_a"] == "cpu"
        assert payload[0]["key_b"] == "memory"
        assert "coefficient" in payload[0]
        assert "strength" in payload[0]


class TestCorrelationReporterHelpers:
    def test_has_strong_true(self):
        r = _make_result(strength=CorrelationStrength.STRONG)
        assert CorrelationReporter([r]).has_strong() is True

    def test_has_strong_false(self):
        r = _make_result(strength=CorrelationStrength.WEAK)
        assert CorrelationReporter([r]).has_strong() is False

    def test_strong_pairs_filters_correctly(self):
        r1 = _make_result(key_a="a", key_b="b", strength=CorrelationStrength.STRONG)
        r2 = _make_result(key_a="c", key_b="d", strength=CorrelationStrength.WEAK)
        reporter = CorrelationReporter([r1, r2])
        pairs = reporter.strong_pairs()
        assert len(pairs) == 1
        assert pairs[0].key_a == "a"
