"""Tee — duplicate metric events to multiple downstream sinks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TeeConfig:
    """Configuration for the Tee duplicator."""
    sinks: List[str] = field(default_factory=list)
    drop_on_error: bool = False
    max_sinks: int = 8

    def __post_init__(self) -> None:
        if self.max_sinks < 1:
            raise ValueError("max_sinks must be at least 1")
        if len(self.sinks) > self.max_sinks:
            raise ValueError(
                f"number of sinks ({len(self.sinks)}) exceeds max_sinks ({self.max_sinks})"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeeConfig":
        return cls(
            sinks=list(data.get("sinks", [])),
            drop_on_error=bool(data.get("drop_on_error", False)),
            max_sinks=int(data.get("max_sinks", 8)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sinks": list(self.sinks),
            "drop_on_error": self.drop_on_error,
            "max_sinks": self.max_sinks,
        }


@dataclass
class TeeResult:
    """Result of a single tee operation."""
    metric_key: str
    sent_to: List[str]
    failed: List[str]

    @property
    def success_count(self) -> int:
        return len(self.sent_to)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "sent_to": list(self.sent_to),
            "failed": list(self.failed),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "all_succeeded": self.all_succeeded,
        }


class Tee:
    """Duplicates metric events to multiple named sinks."""

    def __init__(self, config: TeeConfig) -> None:
        self._config = config

    def distribute(
        self,
        metric_key: str,
        payload: Dict[str, Any],
        sink_map: Dict[str, Any],
    ) -> TeeResult:
        """Send *payload* to every sink listed in config.

        *sink_map* maps sink name -> callable(metric_key, payload).
        Missing or erroring sinks are recorded in ``failed``.
        """
        sent: List[str] = []
        failed: List[str] = []

        for name in self._config.sinks:
            handler = sink_map.get(name)
            if handler is None:
                failed.append(name)
                continue
            try:
                handler(metric_key, payload)
                sent.append(name)
            except Exception:
                if self._config.drop_on_error:
                    failed.append(name)
                else:
                    raise

        return TeeResult(metric_key=metric_key, sent_to=sent, failed=failed)
