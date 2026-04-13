"""Periodic metric rollup: aggregates snapshots into fixed-width time windows."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


@dataclass
class RollupConfig:
    window_seconds: int = 300  # 5-minute windows by default
    max_windows: int = 12      # keep last 12 windows

    @classmethod
    def from_dict(cls, data: dict) -> "RollupConfig":
        return cls(
            window_seconds=int(data.get("window_seconds", 300)),
            max_windows=int(data.get("max_windows", 12)),
        )

    def to_dict(self) -> dict:
        return {"window_seconds": self.window_seconds, "max_windows": self.max_windows}


@dataclass
class RollupWindow:
    start: datetime
    end: datetime
    metric_key: str
    count: int
    mean: float
    minimum: float
    maximum: float

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "metric_key": self.metric_key,
            "count": self.count,
            "mean": round(self.mean, 6),
            "min": round(self.minimum, 6),
            "max": round(self.maximum, 6),
        }


@dataclass
class RollupResult:
    metric_key: str
    windows: List[RollupWindow] = field(default_factory=list)

    def latest(self) -> Optional[RollupWindow]:
        return self.windows[-1] if self.windows else None


class MetricRollup:
    """Buckets MetricHistory snapshots into fixed time windows."""

    def __init__(self, config: Optional[RollupConfig] = None) -> None:
        self._config = config or RollupConfig()

    def rollup(self, history, metric_key: str) -> RollupResult:
        """Compute rollup windows for *metric_key* using *history*."""
        snapshots = history.all(metric_key)
        if not snapshots:
            return RollupResult(metric_key=metric_key)

        step = timedelta(seconds=self._config.window_seconds)
        earliest: datetime = snapshots[0].timestamp
        # align start to a clean multiple of the window
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        offset = int((earliest - epoch).total_seconds())
        aligned_offset = (offset // self._config.window_seconds) * self._config.window_seconds
        window_start = epoch + timedelta(seconds=aligned_offset)

        buckets: Dict[datetime, List[float]] = {}
        for snap in snapshots:
            bucket_offset = int((snap.timestamp - epoch).total_seconds())
            bucket_key = epoch + timedelta(
                seconds=(bucket_offset // self._config.window_seconds) * self._config.window_seconds
            )
            buckets.setdefault(bucket_key, []).append(snap.value)

        sorted_keys = sorted(buckets)[-self._config.max_windows :]
        windows: List[RollupWindow] = []
        for bk in sorted_keys:
            vals = buckets[bk]
            windows.append(
                RollupWindow(
                    start=bk,
                    end=bk + step,
                    metric_key=metric_key,
                    count=len(vals),
                    mean=sum(vals) / len(vals),
                    minimum=min(vals),
                    maximum=max(vals),
                )
            )
        return RollupResult(metric_key=metric_key, windows=windows)
