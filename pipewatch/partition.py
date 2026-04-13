"""Partition-aware metric grouping and summarisation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.metrics import PipelineMetric, MetricStatus


@dataclass
class PartitionConfig:
    key_field: str = "partition"
    max_partitions: int = 64

    @classmethod
    def from_dict(cls, data: dict) -> "PartitionConfig":
        return cls(
            key_field=data.get("key_field", "partition"),
            max_partitions=int(data.get("max_partitions", 64)),
        )

    def to_dict(self) -> dict:
        return {
            "key_field": self.key_field,
            "max_partitions": self.max_partitions,
        }


@dataclass
class PartitionGroup:
    partition_key: str
    metrics: List[PipelineMetric] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.metrics)

    @property
    def worst_status(self) -> MetricStatus:
        if not self.metrics:
            return MetricStatus.OK
        return max(m.status for m in self.metrics)

    @property
    def average_value(self) -> Optional[float]:
        if not self.metrics:
            return None
        return sum(m.value for m in self.metrics) / len(self.metrics)

    def to_dict(self) -> dict:
        return {
            "partition_key": self.partition_key,
            "count": self.count,
            "worst_status": self.worst_status.value,
            "average_value": self.average_value,
        }


@dataclass
class PartitionResult:
    groups: Dict[str, PartitionGroup] = field(default_factory=dict)
    truncated: bool = False

    def to_dict(self) -> dict:
        return {
            "truncated": self.truncated,
            "groups": {k: v.to_dict() for k, v in self.groups.items()},
        }


class PartitionAnalyser:
    def __init__(self, config: Optional[PartitionConfig] = None) -> None:
        self._config = config or PartitionConfig()

    def analyse(
        self, metrics: List[PipelineMetric], partition_values: Dict[str, str]
    ) -> PartitionResult:
        """Group *metrics* by their partition value.

        *partition_values* maps metric key -> partition label.
        """
        groups: Dict[str, PartitionGroup] = {}
        truncated = False

        for metric in metrics:
            label = partition_values.get(metric.key, "__default__")
            if label not in groups:
                if len(groups) >= self._config.max_partitions:
                    truncated = True
                    continue
                groups[label] = PartitionGroup(partition_key=label)
            groups[label].metrics.append(metric)

        return PartitionResult(groups=groups, truncated=truncated)
