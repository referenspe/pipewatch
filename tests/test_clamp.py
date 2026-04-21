"""Tests for pipewatch.clamp."""
import pytest

from pipewatch.clamp import ClampConfig, Clamper, ClampResult


# ---------------------------------------------------------------------------
# ClampConfig
# ---------------------------------------------------------------------------

class TestClampConfig:
    def test_defaults(self):
        cfg = ClampConfig()
        assert cfg.min_value is None
        assert cfg.max_value is None
        assert cfg.clamp_on_violation is False

    def test_from_dict_custom(self):
        cfg = ClampConfig.from_dict({"min_value": 0.0, "max_value": 100.0, "clamp_on_violation": True})
        assert cfg.min_value == 0.0
        assert cfg.max_value == 100.0
        assert cfg.clamp_on_violation is True

    def test_from_dict_defaults_when_missing(self):
        cfg = ClampConfig.from_dict({})
        assert cfg.min_value is None
        assert cfg.max_value is None
        assert cfg.clamp_on_violation is False

    def test_to_dict_round_trip(self):
        cfg = ClampConfig(min_value=1.0, max_value=50.0, clamp_on_violation=True)
        assert ClampConfig.from_dict(cfg.to_dict()).to_dict() == cfg.to_dict()

    def test_raises_if_min_not_less_than_max(self):
        with pytest.raises(ValueError):
            ClampConfig(min_value=10.0, max_value=5.0)

    def test_raises_if_min_equals_max(self):
        with pytest.raises(ValueError):
            ClampConfig(min_value=5.0, max_value=5.0)


# ---------------------------------------------------------------------------
# Clamper.evaluate — no clamping applied to value
# ---------------------------------------------------------------------------

def _clamper(min_v=None, max_v=None, clamp=False) -> Clamper:
    return Clamper(config=ClampConfig(min_value=min_v, max_value=max_v, clamp_on_violation=clamp))


def test_no_violation_within_bounds():
    c = _clamper(min_v=0.0, max_v=100.0)
    r = c.evaluate("cpu", 50.0)
    assert not r.is_violation
    assert r.clamped_value == 50.0


def test_violated_min_detected():
    c = _clamper(min_v=10.0)
    r = c.evaluate("cpu", 5.0)
    assert r.violated_min
    assert not r.violated_max


def test_violated_max_detected():
    c = _clamper(max_v=80.0)
    r = c.evaluate("mem", 95.0)
    assert r.violated_max
    assert not r.violated_min


def test_clamp_on_violation_clamps_to_min():
    c = _clamper(min_v=10.0, clamp=True)
    r = c.evaluate("x", 2.0)
    assert r.clamped_value == 10.0
    assert r.original_value == 2.0


def test_clamp_on_violation_clamps_to_max():
    c = _clamper(max_v=50.0, clamp=True)
    r = c.evaluate("x", 75.0)
    assert r.clamped_value == 50.0


def test_no_clamp_preserves_original_when_flag_false():
    c = _clamper(max_v=50.0, clamp=False)
    r = c.evaluate("x", 75.0)
    assert r.clamped_value == 75.0


def test_violations_filters_only_violations():
    c = _clamper(min_v=0.0, max_v=100.0)
    c.evaluate("a", 50.0)
    c.evaluate("b", -1.0)
    c.evaluate("c", 101.0)
    assert len(c.violations()) == 2


def test_results_accumulate():
    c = _clamper(min_v=0.0, max_v=100.0)
    c.evaluate("a", 10.0)
    c.evaluate("b", 20.0)
    assert len(c.results()) == 2


def test_clear_resets_results():
    c = _clamper(max_v=100.0)
    c.evaluate("a", 50.0)
    c.clear()
    assert c.results() == []


def test_to_dict_contains_expected_keys():
    c = _clamper(min_v=0.0, max_v=10.0)
    r = c.evaluate("z", 5.0)
    d = r.to_dict()
    assert set(d.keys()) == {"key", "original_value", "clamped_value", "violated_min", "violated_max"}
