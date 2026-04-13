"""Pipeline stage dependency tracking and validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class DependencyConfig:
    max_depth: int = 10
    allow_cycles: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "DependencyConfig":
        return cls(
            max_depth=data.get("max_depth", 10),
            allow_cycles=data.get("allow_cycles", False),
        )

    def to_dict(self) -> dict:
        return {"max_depth": self.max_depth, "allow_cycles": self.allow_cycles}


@dataclass
class DependencyResult:
    stage: str
    dependencies: List[str]
    depth: int
    has_cycle: bool
    missing: List[str]

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "dependencies": self.dependencies,
            "depth": self.depth,
            "has_cycle": self.has_cycle,
            "missing": self.missing,
        }


@dataclass
class DependencyGraph:
    _edges: Dict[str, List[str]] = field(default_factory=dict)

    def add_stage(self, stage: str, depends_on: Optional[List[str]] = None) -> None:
        self._edges[stage] = list(depends_on or [])

    def all_stages(self) -> List[str]:
        return list(self._edges.keys())

    def _depth(self, stage: str, visited: Optional[Set[str]] = None) -> int:
        if visited is None:
            visited = set()
        if stage not in self._edges or not self._edges[stage]:
            return 0
        visited.add(stage)
        depths = []
        for dep in self._edges[stage]:
            if dep not in visited:
                depths.append(1 + self._depth(dep, set(visited)))
        return max(depths, default=0)

    def _has_cycle(self, stage: str) -> bool:
        def dfs(node: str, path: Set[str]) -> bool:
            if node in path:
                return True
            if node not in self._edges:
                return False
            path.add(node)
            for dep in self._edges[node]:
                if dfs(dep, path):
                    return True
            path.discard(node)
            return False
        return dfs(stage, set())

    def analyse(self, config: Optional[DependencyConfig] = None) -> List[DependencyResult]:
        cfg = config or DependencyConfig()
        known = set(self._edges.keys())
        results = []
        for stage, deps in self._edges.items():
            missing = [d for d in deps if d not in known]
            depth = self._depth(stage)
            cycle = self._has_cycle(stage)
            results.append(DependencyResult(
                stage=stage,
                dependencies=deps,
                depth=min(depth, cfg.max_depth),
                has_cycle=cycle,
                missing=missing,
            ))
        return results
