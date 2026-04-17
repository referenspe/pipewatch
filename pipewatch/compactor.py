"""Compactor: merges older metric snapshots into coarser time buckets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.history import MetricHistory, MetricSnapshot


@dataclass
class CompactorConfig:
    bucket_seconds: int = 300        # width of each merged bucket
    keep_raw_seconds: int = 600      # age threshold – older snapshots are compacted
    max_buckets: int = 288           # hard cap on stored buckets per key

    @classmethod
    def from_dict(cls, data: dict) -> "CompactorConfig":
        return cls(
            bucket_seconds=data.get("bucket_seconds", 300),
            keep_raw_seconds=data.get("keep_raw_seconds", 600),
            max_buckets=data.get("max_buckets", 288),
        )

    def to_dict(self) -> dict:
        return {
            "bucket_seconds": self.bucket_seconds,
            "keep_raw_seconds": self.keep_raw_seconds,
            "max_buckets": self.max_buckets,
        }


@dataclass
class CompactedBucket:
    bucket_start: float
    count: int
    mean: float
    minimum: float
    maximum: float

    def to_dict(self) -> dict:
        return {
            "bucket_start": self.bucket_start,
            "count": self.count,
            "mean": self.mean,
            "min": self.minimum,
            "max": self.maximum,
        }


@dataclass
class CompactResult:
    key: str
    buckets_created: int
    snapshots_removed: int
    buckets: List[CompactedBucket] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "buckets_created": self.buckets_created,
            "snapshots_removed": self.snapshots_removed,
            "buckets": [b.to_dict() for b in self.buckets],
        }


class Compactor:
    def __init__(self, config: Optional[CompactorConfig] = None) -> None:
        self.config = config or CompactorConfig()
        self._buckets: Dict[str, List[CompactedBucket]] = {}

    def compact(self, key: str, history: MetricHistory, now: float) -> CompactResult:
        cutoff = now - self.config.keep_raw_seconds
        old: List[MetricSnapshot] = [
            s for s in history.snapshots(key) if s.timestamp < cutoff
        ]
        if not old:
            return CompactResult(key=key, buckets_created=0, snapshots_removed=0)

        bucket_map: Dict[int, List[float]] = {}
        for snap in old:
            idx = int(snap.timestamp // self.config.bucket_seconds)
            bucket_map.setdefault(idx, []).append(snap.value)

        new_buckets: List[CompactedBucket] = []
        for idx in sorted(bucket_map):
            vals = bucket_map[idx]
            new_buckets.append(CompactedBucket(
                bucket_start=idx * self.config.bucket_seconds,
                count=len(vals),
                mean=sum(vals) / len(vals),
                minimum=min(vals),
                maximum=max(vals),
            ))

        existing = self._buckets.get(key, [])
        merged = existing + new_buckets
        merged.sort(key=lambda b: b.bucket_start)
        self._buckets[key] = merged[-self.config.max_buckets:]

        history.remove_before(key, cutoff)
        return CompactResult(
            key=key,
            buckets_created=len(new_buckets),
            snapshots_removed=len(old),
            buckets=self._buckets[key],
        )

    def buckets_for(self, key: str) -> List[CompactedBucket]:
        return list(self._buckets.get(key, []))
