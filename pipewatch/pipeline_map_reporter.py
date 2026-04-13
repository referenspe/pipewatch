"""Reporter for rendering a PipelineMap as text or JSON."""
from __future__ import annotations

import json
from typing import List

from pipewatch.pipeline_map import PipelineMap


class PipelineMapReporter:
    """Formats the contents of a PipelineMap for display or export."""

    def __init__(self, pipeline_map: PipelineMap) -> None:
        self._map = pipeline_map

    def has_stages(self) -> bool:
        return bool(self._map.stages())

    def format_text(self) -> str:
        stages = self._map.stages()
        if not stages:
            return "No pipeline stages registered."
        lines: List[str] = ["Pipeline Map:", "=" * 40]
        for name in sorted(stages):
            ups = self._map.upstream(name)
            downs = self._map.downstream(name)
            dep_str = ", ".join(ups) if ups else "(none)"
            dep_down = ", ".join(downs) if downs else "(none)"
            lines.append(f"  {name}")
            lines.append(f"    depends on : {dep_str}")
            lines.append(f"    feeds into : {dep_down}")
        return "\n".join(lines)

    def format_json(self) -> str:
        stages = self._map.stages()
        payload = [
            {
                "name": name,
                "depends_on": self._map.upstream(name),
                "feeds_into": self._map.downstream(name),
            }
            for name in sorted(stages)
        ]
        return json.dumps({"pipeline_map": payload}, indent=2)
