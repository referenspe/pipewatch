"""Baseline management: record and compare metric values against a stored baseline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional
import json
import os

from pipewatch.metrics import PipelineMetric


@dataclass
class BaselineEntry:
    key: str
    value: float
    sample_count: int = 1

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value, "sample_count": self.sample_count}

    @staticmethod
    def from_dict(data: dict) -> "BaselineEntry":
        return BaselineEntry(
            key=data["key"],
            value=float(data["value"]),
            sample_count=int(data.get("sample_count", 1)),
        )


@dataclass
class BaselineDeviation:
    key: str
    baseline_value: float
    current_value: float
    deviation_pct: float  # signed percentage change from baseline

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "deviation_pct": round(self.deviation_pct, 4),
        }


class BaselineStore:
    """Persist and retrieve baseline entries from a JSON file."""

    def __init__(self, path: str = "pipewatch_baseline.json") -> None:
        self._path = path
        self._entries: Dict[str, BaselineEntry] = {}
        if os.path.exists(path):
            self._load()

    # ------------------------------------------------------------------
    def set(self, metric: PipelineMetric) -> None:
        """Record current metric value as the new baseline."""
        self._entries[metric.key] = BaselineEntry(key=metric.key, value=metric.value)
        self._save()

    def get(self, key: str) -> Optional[BaselineEntry]:
        return self._entries.get(key)

    def compare(self, metric: PipelineMetric) -> Optional[BaselineDeviation]:
        """Return deviation from stored baseline, or None if no baseline exists."""
        entry = self._entries.get(metric.key)
        if entry is None:
            return None
        if entry.value == 0.0:
            pct = 0.0 if metric.value == 0.0 else float("inf")
        else:
            pct = (metric.value - entry.value) / abs(entry.value) * 100.0
        return BaselineDeviation(
            key=metric.key,
            baseline_value=entry.value,
            current_value=metric.value,
            deviation_pct=pct,
        )

    def all_keys(self):
        return list(self._entries.keys())

    # ------------------------------------------------------------------
    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump({k: v.to_dict() for k, v in self._entries.items()}, fh, indent=2)

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._entries = {k: BaselineEntry.from_dict(v) for k, v in raw.items()}
