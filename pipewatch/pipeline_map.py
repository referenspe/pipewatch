"""Pipeline map: tracks dependencies between named pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class PipelineMapConfig:
    allow_cycles: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineMapConfig":
        return cls(allow_cycles=data.get("allow_cycles", False))

    def to_dict(self) -> dict:
        return {"allow_cycles": self.allow_cycles}


@dataclass
class StageNode:
    name: str
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "depends_on": list(self.depends_on)}


class CycleDetectedError(Exception):
    """Raised when a dependency cycle is detected and cycles are not allowed."""


class PipelineMap:
    """Stores and queries a directed dependency graph of pipeline stages."""

    def __init__(self, config: Optional[PipelineMapConfig] = None) -> None:
        self._config = config or PipelineMapConfig()
        self._nodes: Dict[str, StageNode] = {}

    def add_stage(self, name: str, depends_on: Optional[List[str]] = None) -> StageNode:
        deps = depends_on or []
        node = StageNode(name=name, depends_on=deps)
        self._nodes[name] = node
        if not self._config.allow_cycles and self._has_cycle():
            del self._nodes[name]
            raise CycleDetectedError(f"Adding '{name}' would create a cycle.")
        return node

    def upstream(self, name: str) -> List[str]:
        """Return direct dependencies of *name*."""
        node = self._nodes.get(name)
        return list(node.depends_on) if node else []

    def downstream(self, name: str) -> List[str]:
        """Return stages that directly depend on *name*."""
        return [n for n, node in self._nodes.items() if name in node.depends_on]

    def all_upstream(self, name: str) -> List[str]:
        """Return all transitive dependencies of *name* (BFS)."""
        visited: List[str] = []
        queue = list(self.upstream(name))
        seen: Set[str] = set(queue)
        while queue:
            current = queue.pop(0)
            visited.append(current)
            for dep in self.upstream(current):
                if dep not in seen:
                    seen.add(dep)
                    queue.append(dep)
        return visited

    def stages(self) -> List[str]:
        return list(self._nodes.keys())

    def _has_cycle(self) -> bool:
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for dep in self._nodes.get(node, StageNode(node)).depends_on:
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in stack:
                    return True
            stack.discard(node)
            return False

        for n in self._nodes:
            if n not in visited:
                if dfs(n):
                    return True
        return False
