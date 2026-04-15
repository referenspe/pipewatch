"""Tests for pipewatch.stagger and pipewatch.stagger_reporter."""
import json
import pytest

from pipewatch.stagger import Stagger, StaggerConfig, StaggerPlan
from pipewatch.stagger_reporter import StaggerReporter


# ---------------------------------------------------------------------------
# StaggerConfig
# ---------------------------------------------------------------------------

class TestStaggerConfig:
    def test_defaults(self):
        cfg = StaggerConfig()
        assert cfg.spread_seconds == 60.0
        assert cfg.jitter_fraction == 0.1
        assert cfg.min_offset_seconds == 0.0

    def test_raises_if_spread_not_positive(self):
        with pytest.raises(ValueError, match="spread_seconds"):
            StaggerConfig(spread_seconds=0)

    def test_raises_if_jitter_out_of_range(self):
        with pytest.raises(ValueError, match="jitter_fraction"):
            StaggerConfig(jitter_fraction=1.5)

    def test_raises_if_min_offset_negative(self):
        with pytest.raises(ValueError, match="min_offset_seconds"):
            StaggerConfig(min_offset_seconds=-1.0)

    def test_from_dict_custom(self):
        cfg = StaggerConfig.from_dict({"spread_seconds": 120.0, "jitter_fraction": 0.05})
        assert cfg.spread_seconds == 120.0
        assert cfg.jitter_fraction == 0.05

    def test_from_dict_defaults_when_missing(self):
        cfg = StaggerConfig.from_dict({})
        assert cfg.spread_seconds == 60.0

    def test_to_dict_round_trip(self):
        cfg = StaggerConfig(spread_seconds=90.0, jitter_fraction=0.2, min_offset_seconds=5.0)
        assert StaggerConfig.from_dict(cfg.to_dict()).spread_seconds == 90.0


# ---------------------------------------------------------------------------
# Stagger.plan
# ---------------------------------------------------------------------------

class TestStaggerPlan:
    def _stagger(self, spread=60.0, jitter=0.0):
        return Stagger(StaggerConfig(spread_seconds=spread, jitter_fraction=jitter))

    def test_empty_targets_returns_empty_plan(self):
        plan = self._stagger().plan([])
        assert plan.offsets == {}

    def test_single_target_gets_zero_offset(self):
        plan = self._stagger().plan(["pipeline_a"], seed=0)
        assert "pipeline_a" in plan.offsets
        assert plan.offsets["pipeline_a"] >= 0

    def test_all_targets_present(self):
        names = ["a", "b", "c"]
        plan = self._stagger().plan(names, seed=42)
        assert set(plan.offsets.keys()) == set(names)

    def test_offsets_increase_monotonically_with_no_jitter(self):
        names = ["x", "y", "z"]
        plan = self._stagger(spread=60.0, jitter=0.0).plan(names, seed=0)
        offsets = [plan.offsets[n] for n in names]
        assert offsets == sorted(offsets)

    def test_slot_size(self):
        s = self._stagger(spread=90.0)
        assert s.slot_size(3) == pytest.approx(30.0)

    def test_slot_size_zero_targets(self):
        s = self._stagger(spread=60.0)
        assert s.slot_size(0) == 60.0

    def test_offset_for_unknown_returns_none(self):
        plan = StaggerPlan(offsets={"a": 5.0})
        assert plan.offset_for("missing") is None

    def test_deterministic_with_same_seed(self):
        s = self._stagger()
        names = ["p", "q", "r"]
        assert self._stagger().plan(names, seed=7).offsets == self._stagger().plan(names, seed=7).offsets


# ---------------------------------------------------------------------------
# StaggerReporter
# ---------------------------------------------------------------------------

class TestStaggerReporter:
    def _reporter(self, names=("alpha", "beta", "gamma"), spread=60.0):
        stagger = Stagger(StaggerConfig(spread_seconds=spread, jitter_fraction=0.0))
        plan = stagger.plan(list(names), seed=0)
        return StaggerReporter(plan)

    def test_empty_plan_message(self):
        reporter = StaggerReporter(StaggerPlan())
        assert "no targets" in reporter.format_text()

    def test_has_targets_false_when_empty(self):
        assert not StaggerReporter(StaggerPlan()).has_targets

    def test_has_targets_true_when_populated(self):
        assert self._reporter().has_targets

    def test_format_text_contains_target_names(self):
        text = self._reporter().format_text()
        assert "alpha" in text
        assert "beta" in text

    def test_format_json_valid(self):
        data = json.loads(self._reporter().format_json())
        assert "offsets" in data

    def test_ordered_targets_sorted_by_offset(self):
        ordered = self._reporter().ordered_targets()
        assert ordered == sorted(ordered, key=lambda n: self._reporter()._plan.offsets[n])

    def test_max_offset_greater_than_min(self):
        r = self._reporter()
        assert r.max_offset() >= r.min_offset()

    def test_max_min_none_when_empty(self):
        r = StaggerReporter(StaggerPlan())
        assert r.max_offset() is None
        assert r.min_offset() is None
