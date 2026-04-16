"""Tests for pipewatch.pruner."""
from unittest.mock import MagicMock

import pytest

from pipewatch.pruner import Pruner, PrunerConfig, PruneResult


def _make_history(key: str, size: int = 5):
    h = MagicMock()
    snapshots = [MagicMock(tags={}) for _ in range(size)]
    h.snapshots.return_value = snapshots
    return h


class TestPrunerConfig:
    def test_defaults(self):
        cfg = PrunerConfig()
        assert cfg.key_patterns == []
        assert cfg.tag_patterns == []
        assert cfg.dry_run is False

    def test_from_dict_custom(self):
        cfg = PrunerConfig.from_dict({"key_patterns": ["tmp_*"], "dry_run": True})
        assert cfg.key_patterns == ["tmp_*"]
        assert cfg.dry_run is True

    def test_from_dict_defaults_when_missing(self):
        cfg = PrunerConfig.from_dict({})
        assert cfg.key_patterns == []
        assert cfg.tag_patterns == []

    def test_to_dict_round_trip(self):
        cfg = PrunerConfig(key_patterns=["a.*"], tag_patterns=["prod"], dry_run=False)
        assert PrunerConfig.from_dict(cfg.to_dict()).key_patterns == ["a.*"]


class TestPruner:
    def test_no_patterns_returns_empty(self):
        pruner = Pruner(PrunerConfig())
        h = _make_history("cpu")
        results = pruner.prune({"cpu": h})
        assert results == []

    def test_key_pattern_matches_and_clears(self):
        pruner = Pruner(PrunerConfig(key_patterns=["tmp_*"]))
        h = _make_history("tmp_job", size=3)
        results = pruner.prune({"tmp_job": h})
        assert len(results) == 1
        assert results[0].key == "tmp_job"
        assert results[0].removed == 3
        h.clear.assert_called_once()

    def test_dry_run_does_not_clear(self):
        pruner = Pruner(PrunerConfig(key_patterns=["tmp_*"], dry_run=True))
        h = _make_history("tmp_job", size=4)
        results = pruner.prune({"tmp_job": h})
        assert results[0].dry_run is True
        h.clear.assert_not_called()

    def test_non_matching_key_not_pruned(self):
        pruner = Pruner(PrunerConfig(key_patterns=["tmp_*"]))
        h = _make_history("cpu")
        results = pruner.prune({"cpu": h})
        assert results == []

    def test_prune_result_to_dict(self):
        r = PruneResult(key="x", removed=2, dry_run=False)
        d = r.to_dict()
        assert d["key"] == "x"
        assert d["removed"] == 2
        assert d["dry_run"] is False

    def test_multiple_keys_partial_match(self):
        pruner = Pruner(PrunerConfig(key_patterns=["drop_*"]))
        h1 = _make_history("drop_old", size=2)
        h2 = _make_history("keep_me", size=3)
        results = pruner.prune({"drop_old": h1, "keep_me": h2})
        assert len(results) == 1
        assert results[0].key == "drop_old"
