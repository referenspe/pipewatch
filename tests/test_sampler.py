"""Tests for pipewatch.sampler."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from pipewatch.sampler import Sampler, SamplerConfig, _TokenBucket


# ---------------------------------------------------------------------------
# SamplerConfig
# ---------------------------------------------------------------------------

class TestSamplerConfig:
    def test_defaults(self):
        cfg = SamplerConfig()
        assert cfg.default_rate == 1.0
        assert cfg.max_burst == 5
        assert cfg.per_key_rates == {}

    def test_from_dict_custom_values(self):
        cfg = SamplerConfig.from_dict(
            {"default_rate": 2.5, "max_burst": 10, "per_key_rates": {"cpu": 0.5}}
        )
        assert cfg.default_rate == 2.5
        assert cfg.max_burst == 10
        assert cfg.per_key_rates == {"cpu": 0.5}

    def test_from_dict_defaults_when_missing(self):
        cfg = SamplerConfig.from_dict({})
        assert cfg.default_rate == 1.0
        assert cfg.max_burst == 5

    def test_to_dict_round_trip(self):
        cfg = SamplerConfig(default_rate=3.0, max_burst=8, per_key_rates={"x": 1.0})
        assert SamplerConfig.from_dict(cfg.to_dict()).default_rate == 3.0


# ---------------------------------------------------------------------------
# _TokenBucket
# ---------------------------------------------------------------------------

class TestTokenBucket:
    def test_allows_up_to_burst(self):
        bucket = _TokenBucket(rate=1.0, max_burst=3)
        results = [bucket.allow() for _ in range(4)]
        assert results[:3] == [True, True, True]
        assert results[3] is False

    def test_refills_over_time(self):
        bucket = _TokenBucket(rate=10.0, max_burst=1)
        assert bucket.allow() is True
        assert bucket.allow() is False
        # Advance time by 0.2 s — enough for 2 tokens at rate=10
        with patch("pipewatch.sampler.time.monotonic", return_value=time.monotonic() + 0.2):
            assert bucket.allow() is True


# ---------------------------------------------------------------------------
# Sampler
# ---------------------------------------------------------------------------

class TestSampler:
    def test_should_sample_returns_true_initially(self):
        sampler = Sampler()
        assert sampler.should_sample("my_metric") is True

    def test_separate_buckets_per_key(self):
        cfg = SamplerConfig(default_rate=1.0, max_burst=1)
        sampler = Sampler(cfg)
        assert sampler.should_sample("a") is True
        assert sampler.should_sample("b") is True   # independent bucket
        assert sampler.should_sample("a") is False

    def test_per_key_rate_applied(self):
        cfg = SamplerConfig(default_rate=100.0, max_burst=1, per_key_rates={"slow": 0.001})
        sampler = Sampler(cfg)
        sampler.should_sample("slow")          # consume the single token
        assert sampler.should_sample("slow") is False
        assert sampler.should_sample("fast") is True  # uses default_rate bucket

    def test_reset_recreates_bucket(self):
        cfg = SamplerConfig(default_rate=1.0, max_burst=1)
        sampler = Sampler(cfg)
        sampler.should_sample("k")  # exhaust
        assert sampler.should_sample("k") is False
        sampler.reset("k")
        assert sampler.should_sample("k") is True

    def test_reset_unknown_key_is_noop(self):
        sampler = Sampler()
        sampler.reset("nonexistent")  # must not raise
