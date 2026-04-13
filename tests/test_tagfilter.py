"""Tests for pipewatch.tagfilter."""
from __future__ import annotations

import pytest

from pipewatch.tagfilter import TagFilter, TagFilterConfig


# ---------------------------------------------------------------------------
# TagFilterConfig
# ---------------------------------------------------------------------------

class TestTagFilterConfig:
    def test_defaults(self):
        cfg = TagFilterConfig()
        assert cfg.include == frozenset()
        assert cfg.exclude == frozenset()
        assert cfg.match_all_include is False

    def test_from_dict_sets_include(self):
        cfg = TagFilterConfig.from_dict({"include": ["prod", "critical"]})
        assert cfg.include == frozenset({"prod", "critical"})

    def test_from_dict_sets_exclude(self):
        cfg = TagFilterConfig.from_dict({"exclude": ["dev"]})
        assert cfg.exclude == frozenset({"dev"})

    def test_from_dict_match_all_include(self):
        cfg = TagFilterConfig.from_dict({"match_all_include": True})
        assert cfg.match_all_include is True

    def test_from_dict_defaults_when_missing(self):
        cfg = TagFilterConfig.from_dict({})
        assert cfg.include == frozenset()
        assert cfg.exclude == frozenset()
        assert cfg.match_all_include is False

    def test_to_dict_round_trip(self):
        original = TagFilterConfig.from_dict(
            {"include": ["prod"], "exclude": ["dev"], "match_all_include": True}
        )
        restored = TagFilterConfig.from_dict(original.to_dict())
        assert restored == original


# ---------------------------------------------------------------------------
# TagFilter.passes
# ---------------------------------------------------------------------------

class TestTagFilterPasses:
    def _make_filter(self, **kwargs) -> TagFilter:
        return TagFilter(config=TagFilterConfig.from_dict(kwargs))

    def test_no_rules_passes_everything(self):
        f = self._make_filter()
        assert f.passes(["prod", "critical"]) is True
        assert f.passes([]) is True

    def test_include_or_semantics_match(self):
        f = self._make_filter(include=["prod"])
        assert f.passes(["prod", "staging"]) is True

    def test_include_or_semantics_no_match(self):
        f = self._make_filter(include=["prod"])
        assert f.passes(["staging"]) is False

    def test_include_and_semantics_all_present(self):
        f = self._make_filter(include=["prod", "critical"], match_all_include=True)
        assert f.passes(["prod", "critical", "eu"]) is True

    def test_include_and_semantics_partial_fails(self):
        f = self._make_filter(include=["prod", "critical"], match_all_include=True)
        assert f.passes(["prod"]) is False

    def test_exclude_blocks_match(self):
        f = self._make_filter(include=["prod"], exclude=["dev"])
        assert f.passes(["prod", "dev"]) is False

    def test_exclude_without_include_blocks(self):
        f = self._make_filter(exclude=["dev"])
        assert f.passes(["dev"]) is False
        assert f.passes(["prod"]) is True


# ---------------------------------------------------------------------------
# TagFilter.filter
# ---------------------------------------------------------------------------

class TestTagFilterFilter:
    def test_filters_list_by_key(self):
        items = [
            {"name": "a", "tags": ["prod"]},
            {"name": "b", "tags": ["dev"]},
            {"name": "c", "tags": ["prod", "critical"]},
        ]
        f = TagFilter(config=TagFilterConfig.from_dict({"include": ["prod"]}))
        result = f.filter(items, key=lambda x: x["tags"])
        names = [i["name"] for i in result]
        assert names == ["a", "c"]

    def test_returns_all_when_no_rules(self):
        items = [["prod"], ["dev"], []]
        f = TagFilter(config=TagFilterConfig())
        assert f.filter(items, key=lambda x: x) == items
