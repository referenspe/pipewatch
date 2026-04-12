"""Periodic digest summaries for pipeline health reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pipewatch.aggregator import MetricSummary
from pipewatch.metrics import MetricStatus


@dataclass
class DigestConfig:
    """Configuration for digest generation."""
    title: str = "Pipeline Health Digest"
    include_ok: bool = False
    max_entries: int = 50

    @classmethod
    def from_dict(cls, data: Dict) -> "DigestConfig":
        return cls(
            title=data.get("title", "Pipeline Health Digest"),
            include_ok=data.get("include_ok", False),
            max_entries=int(data.get("max_entries", 50)),
        )

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "include_ok": self.include_ok,
            "max_entries": self.max_entries,
        }


@dataclass
class DigestEntry:
    """A single entry in a digest report."""
    metric_key: str
    status: MetricStatus
    summary: MetricSummary

    def to_dict(self) -> Dict:
        return {
            "metric_key": self.metric_key,
            "status": self.status.value,
            "summary": self.summary.to_dict(),
        }


@dataclass
class Digest:
    """A compiled digest of pipeline health across all tracked metrics."""
    title: str
    generated_at: datetime
    entries: List[DigestEntry] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for e in self.entries if e.status == MetricStatus.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.entries if e.status == MetricStatus.WARNING)

    @property
    def ok_count(self) -> int:
        return sum(1 for e in self.entries if e.status == MetricStatus.OK)

    @property
    def overall_status(self) -> MetricStatus:
        if self.critical_count > 0:
            return MetricStatus.CRITICAL
        if self.warning_count > 0:
            return MetricStatus.WARNING
        return MetricStatus.OK

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "overall_status": self.overall_status.value,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "ok_count": self.ok_count,
            "entries": [e.to_dict() for e in self.entries],
        }


class DigestBuilder:
    """Builds a Digest from aggregated metric summaries."""

    def __init__(self, config: Optional[DigestConfig] = None) -> None:
        self.config = config or DigestConfig()

    def build(
        self,
        summaries: Dict[str, MetricSummary],
        statuses: Dict[str, MetricStatus],
        now: Optional[datetime] = None,
    ) -> Digest:
        generated_at = now or datetime.now(timezone.utc)
        entries: List[DigestEntry] = []

        for key, summary in summaries.items():
            status = statuses.get(key, MetricStatus.OK)
            if not self.config.include_ok and status == MetricStatus.OK:
                continue
            entries.append(DigestEntry(metric_key=key, status=status, summary=summary))

        entries.sort(key=lambda e: e.status.value, reverse=True)
        entries = entries[: self.config.max_entries]

        return Digest(
            title=self.config.title,
            generated_at=generated_at,
            entries=entries,
        )
