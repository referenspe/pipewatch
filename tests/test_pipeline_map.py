"""Tests for pipewatch.pipeline_map."""
import pytest

from pipewatch.pipeline_map import (
    CycleDetectedError,
    PipelineMap,
    PipelineMapConfig,
    StageNode,
)


# ---------------------------------------------------------------------------
# PipelineMapConfig
# ---------------------------------------------------------------------------

class TestPipelineMapConfig:
    def test_defaults(self):
        cfg = PipelineMapConfig()
        assert cfg.allow_cycles is False

    def test_from_dict_custom(self):
        cfg = PipelineMapConfig.from_dict({"allow_cycles": True})
        assert cfg.allow_cycles is True

    def test_from_dict_defaults_when_missing(self):
        cfg = PipelineMapConfig.from_dict({})
        assert cfg.allow_cycles is False

    def test_to_dict_round_trip(self):
        cfg = PipelineMapConfig(allow_cycles=True)
        assert PipelineMapConfig.from_dict(cfg.to_dict()).allow_cycles is True


# ---------------------------------------------------------------------------
# StageNode
# ---------------------------------------------------------------------------

def test_stage_node_to_dict():
    node = StageNode(name="ingest", depends_on=["raw"])
    d = node.to_dict()
    assert d["name"] == "ingest"
    assert d["depends_on"] == ["raw"]


# ---------------------------------------------------------------------------
# PipelineMap – basic operations
# ---------------------------------------------------------------------------

class TestPipelineMapBasic:
    def _simple_map(self) -> PipelineMap:
        pm = PipelineMap()
        pm.add_stage("ingest")
        pm.add_stage("validate", depends_on=["ingest"])
        pm.add_stage("load", depends_on=["validate"])
        return pm

    def test_stages_returns_all_names(self):
        pm = self._simple_map()
        assert set(pm.stages()) == {"ingest", "validate", "load"}

    def test_upstream_returns_direct_deps(self):
        pm = self._simple_map()
        assert pm.upstream("validate") == ["ingest"]

    def test_upstream_empty_for_root(self):
        pm = self._simple_map()
        assert pm.upstream("ingest") == []

    def test_upstream_unknown_stage_returns_empty(self):
        pm = self._simple_map()
        assert pm.upstream("ghost") == []

    def test_downstream_returns_dependents(self):
        pm = self._simple_map()
        assert pm.downstream("ingest") == ["validate"]

    def test_downstream_empty_for_leaf(self):
        pm = self._simple_map()
        assert pm.downstream("load") == []

    def test_all_upstream_transitive(self):
        pm = self._simple_map()
        result = pm.all_upstream("load")
        assert "validate" in result
        assert "ingest" in result

    def test_all_upstream_empty_for_root(self):
        pm = self._simple_map()
        assert pm.all_upstream("ingest") == []


# ---------------------------------------------------------------------------
# PipelineMap – cycle detection
# ---------------------------------------------------------------------------

class TestPipelineMapCycles:
    def test_raises_on_direct_cycle(self):
        pm = PipelineMap()
        pm.add_stage("a", depends_on=["b"])
        with pytest.raises(CycleDetectedError):
            pm.add_stage("b", depends_on=["a"])

    def test_stage_not_added_after_cycle_error(self):
        pm = PipelineMap()
        pm.add_stage("a", depends_on=["b"])
        try:
            pm.add_stage("b", depends_on=["a"])
        except CycleDetectedError:
            pass
        assert "b" not in pm.stages()

    def test_allows_cycle_when_configured(self):
        cfg = PipelineMapConfig(allow_cycles=True)
        pm = PipelineMap(config=cfg)
        pm.add_stage("a", depends_on=["b"])
        pm.add_stage("b", depends_on=["a"])  # should not raise
        assert "b" in pm.stages()
