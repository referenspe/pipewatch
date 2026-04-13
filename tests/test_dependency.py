"""Tests for pipewatch.dependency and pipewatch.dependency_reporter."""
import json
import pytest

from pipewatch.dependency import DependencyConfig, DependencyGraph
from pipewatch.dependency_reporter import DependencyReporter


# ---------------------------------------------------------------------------
# DependencyConfig
# ---------------------------------------------------------------------------

class TestDependencyConfig:
    def test_defaults(self):
        cfg = DependencyConfig()
        assert cfg.max_depth == 10
        assert cfg.allow_cycles is False

    def test_from_dict_custom(self):
        cfg = DependencyConfig.from_dict({"max_depth": 5, "allow_cycles": True})
        assert cfg.max_depth == 5
        assert cfg.allow_cycles is True

    def test_from_dict_defaults_when_missing(self):
        cfg = DependencyConfig.from_dict({})
        assert cfg.max_depth == 10
        assert cfg.allow_cycles is False

    def test_to_dict_round_trip(self):
        cfg = DependencyConfig(max_depth=3, allow_cycles=True)
        assert DependencyConfig.from_dict(cfg.to_dict()).max_depth == 3


# ---------------------------------------------------------------------------
# DependencyGraph.analyse
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def _simple_graph(self) -> DependencyGraph:
        g = DependencyGraph()
        g.add_stage("ingest")
        g.add_stage("transform", depends_on=["ingest"])
        g.add_stage("load", depends_on=["transform"])
        return g

    def test_all_stages_returned(self):
        g = self._simple_graph()
        results = g.analyse()
        names = {r.stage for r in results}
        assert names == {"ingest", "transform", "load"}

    def test_depth_increases_with_chain(self):
        g = self._simple_graph()
        results = {r.stage: r for r in g.analyse()}
        assert results["ingest"].depth == 0
        assert results["transform"].depth == 1
        assert results["load"].depth == 2

    def test_no_cycle_in_linear_graph(self):
        g = self._simple_graph()
        assert all(not r.has_cycle for r in g.analyse())

    def test_cycle_detected(self):
        g = DependencyGraph()
        g.add_stage("a", depends_on=["b"])
        g.add_stage("b", depends_on=["a"])
        results = {r.stage: r for r in g.analyse()}
        assert results["a"].has_cycle is True

    def test_missing_dependency_flagged(self):
        g = DependencyGraph()
        g.add_stage("transform", depends_on=["ingest"])
        results = g.analyse()
        assert results[0].missing == ["ingest"]

    def test_no_missing_when_all_declared(self):
        g = self._simple_graph()
        assert all(r.missing == [] for r in g.analyse())


# ---------------------------------------------------------------------------
# DependencyReporter
# ---------------------------------------------------------------------------

class TestDependencyReporter:
    def _reporter(self) -> DependencyReporter:
        g = DependencyGraph()
        g.add_stage("ingest")
        g.add_stage("transform", depends_on=["ingest"])
        return DependencyReporter(g.analyse())

    def test_empty_results_message(self):
        r = DependencyReporter([])
        assert "No dependency" in r.format_text()

    def test_format_text_contains_stage_name(self):
        assert "transform" in self._reporter().format_text()

    def test_format_text_contains_depth(self):
        assert "depth=" in self._reporter().format_text()

    def test_has_cycles_false_for_clean_graph(self):
        assert self._reporter().has_cycles() is False

    def test_has_cycles_true_when_cycle_present(self):
        g = DependencyGraph()
        g.add_stage("a", depends_on=["b"])
        g.add_stage("b", depends_on=["a"])
        r = DependencyReporter(g.analyse())
        assert r.has_cycles() is True

    def test_has_missing_false_for_clean_graph(self):
        assert self._reporter().has_missing() is False

    def test_format_json_is_valid(self):
        data = json.loads(self._reporter().format_json())
        assert "stages" in data
        assert isinstance(data["stages"], list)

    def test_format_json_has_cycles_key(self):
        data = json.loads(self._reporter().format_json())
        assert "has_cycles" in data
