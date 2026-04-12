"""Rate-limiting sampler that controls how frequently metric values are collected."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SamplerConfig:
    """Configuration for the metric sampler."""
    default_rate: float = 1.0        # samples per second
    max_burst: int = 5               # maximum burst size
    per_key_rates: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SamplerConfig":
        return cls(
            default_rate=float(data.get("default_rate", 1.0)),
            max_burst=int(data.get("max_burst", 5)),
            per_key_rates={
                k: float(v) for k, v in data.get("per_key_rates", {}).items()
            },
        )

    def to_dict(self) -> dict:
        return {
            "default_rate": self.default_rate,
            "max_burst": self.max_burst,
            "per_key_rates": dict(self.per_key_rates),
        }


@dataclass
class _TokenBucket:
    rate: float
    max_burst: int
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.max_burst)
        self._last_refill = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self.max_burst),
            self._tokens + elapsed * self.rate,
        )
        self._last_refill = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


class Sampler:
    """Token-bucket sampler; call :meth:`should_sample` before recording a metric."""

    def __init__(self, config: Optional[SamplerConfig] = None) -> None:
        self._config = config or SamplerConfig()
        self._buckets: Dict[str, _TokenBucket] = {}

    def _bucket_for(self, key: str) -> _TokenBucket:
        if key not in self._buckets:
            rate = self._config.per_key_rates.get(key, self._config.default_rate)
            self._buckets[key] = _TokenBucket(
                rate=rate, max_burst=self._config.max_burst
            )
        return self._buckets[key]

    def should_sample(self, key: str) -> bool:
        """Return True if a sample for *key* is permitted right now."""
        return self._bucket_for(key).allow()

    def reset(self, key: str) -> None:
        """Discard the bucket for *key* so it is recreated on next access."""
        self._buckets.pop(key, None)
