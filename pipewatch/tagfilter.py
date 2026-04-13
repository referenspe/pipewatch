"""Tag-based filtering for pipeline metrics and alert events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional


@dataclass
class TagFilterConfig:
    """Configuration for tag-based filtering."""

    include: FrozenSet[str] = field(default_factory=frozenset)
    exclude: FrozenSet[str] = field(default_factory=frozenset)
    match_all_include: bool = False  # True = AND semantics; False = OR semantics

    @staticmethod
    def from_dict(data: Dict) -> "TagFilterConfig":
        return TagFilterConfig(
            include=frozenset(data.get("include", [])),
            exclude=frozenset(data.get("exclude", [])),
            match_all_include=bool(data.get("match_all_include", False)),
        )

    def to_dict(self) -> Dict:
        return {
            "include": sorted(self.include),
            "exclude": sorted(self.exclude),
            "match_all_include": self.match_all_include,
        }


@dataclass
class TagFilter:
    """Applies a TagFilterConfig to decide whether a tagged item passes."""

    config: TagFilterConfig

    def passes(self, tags: Iterable[str]) -> bool:
        """Return True if *tags* satisfies the filter rules."""
        tag_set: FrozenSet[str] = frozenset(tags)

        # Exclusion always wins.
        if self.config.exclude and tag_set & self.config.exclude:
            return False

        # If no include rules, everything (not excluded) passes.
        if not self.config.include:
            return True

        if self.config.match_all_include:
            return self.config.include <= tag_set  # all required tags present
        return bool(tag_set & self.config.include)  # at least one match

    def filter(self, items: List, *, key=lambda x: x) -> List:
        """Return the subset of *items* whose tags pass the filter.

        *key* must be a callable that extracts an iterable of tag strings from
        each item.
        """
        return [item for item in items if self.passes(key(item))]
