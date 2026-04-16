"""Pruner: remove metrics from history that match tag or key patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List

from pipewatch.history import MetricHistory


@dataclass
class PrunerConfig:
    key_patterns: List[str] = field(default_factory=list)
    tag_patterns: List[str] = field(default_factory=list)
    dry_run: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "PrunerConfig":
        return cls(
            key_patterns=data.get("key_patterns", []),
            tag_patterns=data.get("tag_patterns", []),
            dry_run=data.get("dry_run", False),
        )

    def to_dict(self) -> dict:
        return {
            "key_patterns": self.key_patterns,
            "tag_patterns": self.tag_patterns,
            "dry_run": self.dry_run,
        }


@dataclass
class PruneResult:
    key: str
    removed: int
    dry_run: bool

    def to_dict(self) -> dict:
        return {"key": self.key, "removed": self.removed, "dry_run": self.dry_run}


class Pruner:
    def __init__(self, config: PrunerConfig) -> None:
        self.config = config

    def _key_matches(self, key: str) -> bool:
        return any(fnmatch(key, p) for p in self.config.key_patterns)

    def _tags_match(self, tags: dict) -> bool:
        return any(
            fnmatch(str(v), p)
            for p in self.config.tag_patterns
            for v in tags.values()
        )

    def prune(self, histories: dict[str, MetricHistory]) -> List[PruneResult]:
        results: List[PruneResult] = []
        for key, history in list(histories.items()):
            snapshots = history.snapshots()
            before = len(snapshots)
            if self._key_matches(key):
                if not self.config.dry_run:
                    history.clear()
                results.append(PruneResult(key=key, removed=before, dry_run=self.config.dry_run))
                continue
            if self.config.tag_patterns:
                to_keep = [
                    s for s in snapshots
                    if not self._tags_match(getattr(s, "tags", {}))
                ]
                removed = before - len(to_keep)
                if removed:
                    if not self.config.dry_run:
                        history.replace(to_keep)
                    results.append(PruneResult(key=key, removed=removed, dry_run=self.config.dry_run))
        return results
