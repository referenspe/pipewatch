"""Clamp module: enforces value bounds on pipeline metrics and reports violations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ClampConfig:
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    clamp_on_violation: bool = False  # if True, record clamped value; else just report

    def __post_init__(self) -> None:
        if self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                raise ValueError("min_value must be strictly less than max_value")

    @classmethod
    def from_dict(cls, data: dict) -> "ClampConfig":
        return cls(
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            clamp_on_violation=data.get("clamp_on_violation", False),
        )

    def to_dict(self) -> dict:
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
            "clamp_on_violation": self.clamp_on_violation,
        }


@dataclass
class ClampResult:
    key: str
    original_value: float
    clamped_value: float
    violated_min: bool
    violated_max: bool

    @property
    def is_violation(self) -> bool:
        return self.violated_min or self.violated_max

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "original_value": self.original_value,
            "clamped_value": self.clamped_value,
            "violated_min": self.violated_min,
            "violated_max": self.violated_max,
        }


@dataclass
class Clamper:
    config: ClampConfig
    _results: List[ClampResult] = field(default_factory=list, init=False)

    def evaluate(self, key: str, value: float) -> ClampResult:
        violated_min = self.config.min_value is not None and value < self.config.min_value
        violated_max = self.config.max_value is not None and value > self.config.max_value

        if self.config.clamp_on_violation:
            clamped = value
            if violated_min:
                clamped = self.config.min_value  # type: ignore[assignment]
            elif violated_max:
                clamped = self.config.max_value  # type: ignore[assignment]
        else:
            clamped = value

        result = ClampResult(
            key=key,
            original_value=value,
            clamped_value=clamped,
            violated_min=violated_min,
            violated_max=violated_max,
        )
        self._results.append(result)
        return result

    def results(self) -> List[ClampResult]:
        return list(self._results)

    def violations(self) -> List[ClampResult]:
        return [r for r in self._results if r.is_violation]

    def clear(self) -> None:
        self._results.clear()
