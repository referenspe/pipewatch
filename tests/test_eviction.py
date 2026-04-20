"""Tests for pipewatch.eviction and pipewatch.eviction_reporter."""
import pytest

from pipewatch.eviction import Eviction, EvictionConfig, EvictionResult
from pipewatch.eviction_reporter import EvictionReporter


# ---------------------------------------------------------------------------
# EvictionConfig
# ---------------------------------------------------------------------------

class TestEvictionConfig:
    def test_defaults(self):
        cfg = EvictionConfig()
        assert cfg.max_keys == 100
        assert cfg.evict_after_seconds == 3600
        assert cfg.evict_on_ok_streak == 0

    def test_from_dict_custom(self):
        cfg = EvictionConfig.from_dict({"max_keys": 10, "evict_after_seconds": 60, "evict_on_ok_streak": 5})
        assert cfg.max_keys == 10
        assert cfg.evict_after_seconds == 60
        assert cfg.evict_on_ok_streak == 5

    def test_from_dict_defaults_when_missing(self):
        cfg = EvictionConfig.from_dict({})
        assert cfg.max_keys == 100

    def test_to_dict_round_trip(self):
        cfg = EvictionConfig(max_keys=50, evict_after_seconds=120, evict_on_ok_streak=3)
        assert EvictionConfig.from_dict(cfg.to_dict()).max_keys == 50


# ---------------------------------------------------------------------------
# Eviction.evaluate — stale reason
# ---------------------------------------------------------------------------

def test_evicts_stale_key():
    ev = Eviction(config=EvictionConfig(evict_after_seconds=10))
    ev.record("pipeline.a", is_ok=False, now=0.0)
    results = ev.evaluate(now=11.0)
    assert len(results) == 1
    assert results[0].key == "pipeline.a"
    assert results[0].reason == "stale"


def test_does_not_evict_fresh_key():
    ev = Eviction(config=EvictionConfig(evict_after_seconds=10))
    ev.record("pipeline.a", is_ok=False, now=0.0)
    results = ev.evaluate(now=5.0)
    assert results == []


# ---------------------------------------------------------------------------
# Eviction.evaluate — ok_streak reason
# ---------------------------------------------------------------------------

def test_evicts_on_ok_streak():
    ev = Eviction(config=EvictionConfig(evict_on_ok_streak=3, evict_after_seconds=9999))
    for _ in range(3):
        ev.record("pipeline.b", is_ok=True, now=0.0)
    results = ev.evaluate(now=1.0)
    assert len(results) == 1
    assert results[0].reason == "ok_streak"
    assert results[0].ok_streak == 3


def test_ok_streak_resets_on_non_ok():
    ev = Eviction(config=EvictionConfig(evict_on_ok_streak=3, evict_after_seconds=9999))
    ev.record("pipeline.b", is_ok=True, now=0.0)
    ev.record("pipeline.b", is_ok=False, now=0.0)
    ev.record("pipeline.b", is_ok=True, now=0.0)
    results = ev.evaluate(now=1.0)
    assert results == []


# ---------------------------------------------------------------------------
# Eviction.evaluate — capacity reason
# ---------------------------------------------------------------------------

def test_evicts_oldest_when_over_capacity():
    ev = Eviction(config=EvictionConfig(max_keys=2, evict_after_seconds=9999))
    ev.record("old", is_ok=False, now=0.0)
    ev.record("mid", is_ok=False, now=1.0)
    ev.record("new", is_ok=False, now=2.0)
    results = ev.evaluate(now=3.0)
    assert len(results) == 1
    assert results[0].key == "old"
    assert results[0].reason == "capacity"


# ---------------------------------------------------------------------------
# active_keys
# ---------------------------------------------------------------------------

def test_active_keys_excludes_evicted():
    ev = Eviction(config=EvictionConfig(evict_after_seconds=5))
    ev.record("a", is_ok=False, now=0.0)
    ev.record("b", is_ok=False, now=0.0)
    ev.evaluate(now=10.0)
    assert ev.active_keys() == []


# ---------------------------------------------------------------------------
# EvictionReporter
# ---------------------------------------------------------------------------

def _make_result(key="k", reason="stale", age=30.0, streak=0):
    return EvictionResult(key=key, reason=reason, age_seconds=age, ok_streak=streak)


class TestEvictionReporterText:
    def test_empty_results_message(self):
        r = EvictionReporter([])
        assert "no keys evicted" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert not EvictionReporter([]).has_results

    def test_has_results_true_when_populated(self):
        assert EvictionReporter([_make_result()]).has_results

    def test_total_evicted(self):
        r = EvictionReporter([_make_result(), _make_result(key="x")])
        assert r.total_evicted == 2

    def test_contains_key_name(self):
        r = EvictionReporter([_make_result(key="pipeline.x")])
        assert "pipeline.x" in r.format_text()

    def test_contains_reason(self):
        r = EvictionReporter([_make_result(reason="capacity")])
        assert "CAPACITY" in r.format_text()

    def test_by_reason_filters_correctly(self):
        results = [_make_result(reason="stale"), _make_result(reason="ok_streak")]
        r = EvictionReporter(results)
        assert len(r.by_reason("stale")) == 1

    def test_format_json_contains_total(self):
        import json
        r = EvictionReporter([_make_result()])
        data = json.loads(r.format_json())
        assert data["total_evicted"] == 1
        assert len(data["evictions"]) == 1
