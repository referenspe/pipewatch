"""Tests for pipewatch.circuit_breaker."""
from datetime import datetime, timedelta

import pytest

from pipewatch.circuit_breaker import (
    BreakerState,
    CircuitBreaker,
    CircuitBreakerConfig,
)


# ---------------------------------------------------------------------------
# CircuitBreakerConfig
# ---------------------------------------------------------------------------

class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold == 5
        assert cfg.recovery_timeout == 60
        assert cfg.success_threshold == 2

    def test_raises_if_failure_threshold_zero(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)

    def test_raises_if_recovery_timeout_notwith pytest.raises(ValueError):
            CircuitBreakerConfig(recovery_timeout=0)

    def test_raises_if_success_threshold_zero(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(success_threshold=0)

    def test_from_dict_custom(self):
        cfg = CircuitBreakerConfig.from_dict(
            {"failure_threshold": 3, "recovery_timeout": 30, "success_threshold": 1}
        )
        assert cfg.failure_threshold == 3
        assert cfg.recovery_timeout == 30
        assert cfg.success_threshold == 1

    def test_from_dict_defaults_when_missing(self):
        cfg = CircuitBreakerConfig.from_dict({})
        assert cfg.failure_threshold == 5

    def test_to_dict_round_trip(self):
        cfg = CircuitBreakerConfig(failure_threshold=4, recovery_timeout=45, success_threshold=3)
        assert CircuitBreakerConfig.from_dict(cfg.to_dict()) == cfg


# ---------------------------------------------------------------------------
# CircuitBreaker behaviour
# ---------------------------------------------------------------------------

def _breaker(failure_threshold=3, recovery_timeout=30, success_threshold=2):
    cfg = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold,
    )
    return CircuitBreaker(cfg)


class TestCircuitBreakerClosed:
    def test_initially_allowed(self):
        cb = _breaker()
        result = cb.is_allowed("pipeline_a")
        assert result.allowed is True
        assert result.state == BreakerState.CLOSED

    def test_stays_closed_below_threshold(self):
        cb = _breaker(failure_threshold=3)
        for _ in range(2):
            cb.record_failure("k")
        assert cb.is_allowed("k").state == BreakerState.CLOSED

    def test_opens_at_threshold(self):
        cb = _breaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure("k")
        result = cb.is_allowed("k")
        assert result.state == BreakerState.OPEN
        assert result.allowed is False


class TestCircuitBreakerOpen:
    def test_blocked_while_open(self):
        cb = _breaker(failure_threshold=1, recovery_timeout=60)
        now = datetime(2024, 1, 1, 12, 0, 0)
        cb.record_failure("k", now=now)
        result = cb.is_allowed("k", now=now + timedelta(seconds=10))
        assert result.allowed is False

    def test_transitions_to_half_open_after_timeout(self):
        cb = _breaker(failure_threshold=1, recovery_timeout=30)
        now = datetime(2024, 1, 1, 12, 0, 0)
        cb.record_failure("k", now=now)
        result = cb.is_allowed("k", now=now + timedelta(seconds=31))
        assert result.state == BreakerState.HALF_OPEN
        assert result.allowed is True


class TestCircuitBreakerHalfOpen:
    def test_failure_in_half_open_reopens(self):
        cb = _breaker(failure_threshold=1, recovery_timeout=1)
        now = datetime(2024, 1, 1, 12, 0, 0)
        cb.record_failure("k", now=now)
        cb.is_allowed("k", now=now + timedelta(seconds=2))  # transition to half-open
        cb.record_failure("k", now=now + timedelta(seconds=2))
        result = cb.is_allowed("k", now=now + timedelta(seconds=2))
        assert result.state == BreakerState.OPEN

    def test_enough_successes_close_breaker(self):
        cb = _breaker(failure_threshold=1, recovery_timeout=1, success_threshold=2)
        now = datetime(2024, 1, 1, 12, 0, 0)
        cb.record_failure("k", now=now)
        cb.is_allowed("k", now=now + timedelta(seconds=2))  # → half-open
        cb.record_success("k")
        cb.record_success("k")
        result = cb.is_allowed("k")
        assert result.state == BreakerState.CLOSED
        assert result.allowed is True
