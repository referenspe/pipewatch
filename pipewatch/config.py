"""Configuration loading and validation for pipewatch."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipewatch.metrics import ThresholdConfig


@dataclass
class TargetConfig:
    name: str
    metric_key: str
    threshold: ThresholdConfig
    interval_seconds: float = 60.0
    tags: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetConfig":
        threshold_data = data.get("threshold", {})
        threshold = ThresholdConfig(
            warning=threshold_data.get("warning"),
            critical=threshold_data.get("critical"),
            comparison=threshold_data.get("comparison", "gt"),
        )
        return cls(
            name=data["name"],
            metric_key=data["metric_key"],
            threshold=threshold,
            interval_seconds=data.get("interval_seconds", 60.0),
            tags=data.get("tags", {}),
        )


@dataclass
class PipewatchConfig:
    targets: list[TargetConfig] = field(default_factory=list)
    log_level: str = "INFO"
    alert_channels: list[str] = field(default_factory=lambda: ["logging"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipewatchConfig":
        targets = [TargetConfig.from_dict(t) for t in data.get("targets", [])]
        return cls(
            targets=targets,
            log_level=data.get("log_level", "INFO"),
            alert_channels=data.get("alert_channels", ["logging"]),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "PipewatchConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with path.open() as fh:
            data = json.load(fh)
        return cls.from_dict(data)
