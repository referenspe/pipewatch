"""Tests for pipewatch.compactor and pipewatch.compactor_reporter."""
from __future__ import annotations

import time
import pytest

from pipewatch.compactor import Compactor, CompactorConfig, CompactedBucket
from pipewatch.compactor_reporter import CompactorReporter
from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_history(key: str, values_and_ages):
    """Build a MetricHistory pre-populated with snapshots.

    values_and_ages: list of (value, age_seconds_ago)
    """
    now = time.time()
    h = MetricHistory()
    for value, age in values_and_ages:
        h._store.setdefault(key, [])  # type: ignore[attr-defined]
        from pipewatch.history import MetricSnapshot
        h._store[key].append(  # type: ignore[attr-defined]
            MetricSnapshot(key=key, value=value, status=MetricStatus.OK,
                           timestamp=now - age)
        )
    return h, now


# ---------------------------------------------------------------------------
# CompactorConfig
# ---------------------------------------------------------------------------

class TestCompactorConfig:
    def test_defaults(self):
        c = CompactorConfig()
        assert c.bucket_seconds == 300
        assert c.keep_raw_seconds == 600
        assert c.max_buckets == 288

    def test_from_dict_custom(self):
        c = CompactorConfig.from_dict({"bucket_seconds": 60, "keep_raw_seconds": 120, "max_buckets": 10})
        assert c.bucket_seconds == 60
        assert c.keep_raw_seconds == 120
        assert c.max_buckets == 10

    def test_from_dict_defaults_when_missing(self):
        c = CompactorConfig.from_dict({})
        assert c.bucket_seconds == 300

    def test_to_dict_round_trip(self):
        c = CompactorConfig(bucket_seconds=120, keep_raw_seconds=240, max_buckets=50)
        assert CompactorConfig.from_dict(c.to_dict()).bucket_seconds == 120


# ---------------------------------------------------------------------------
# Compactor.compact
# ---------------------------------------------------------------------------

class TestCompactorCompact:
    def test_no_old_snapshots_returns_empty_result(self):
        cfg = CompactorConfig(keep_raw_seconds=600)
        c = Compactor(cfg)
        h, now = _make_history("cpu", [(50.0, 10), (60.0, 20)])  # recent
        result = c.compact("cpu", h, now)
        assert result.snapshots_removed == 0
        assert result.buckets_created == 0

    def test_old_snapshots_are_compacted(self):
        cfg = CompactorConfig(keep_raw_seconds=100, bucket_seconds=300)
        c = Compactor(cfg)
        h, now = _make_history("cpu", [(10.0, 200), (20.0, 250), (30.0, 800)])
        result = c.compact("cpu", h, now)
        assert result.snapshots_removed == 3
        assert result.buckets_created >= 1

    def test_bucket_mean_is_correct(self):
        cfg = CompactorConfig(keep_raw_seconds=0, bucket_seconds=10_000)
        c = Compactor(cfg)
        h, now = _make_history("q", [(10.0, 100), (20.0, 200)])
        result = c.compact("q", h, now)
        assert len(result.buckets) == 1
        assert result.buckets[0].mean == pytest.approx(15.0)

    def test_max_buckets_respected(self):
        cfg = CompactorConfig(keep_raw_seconds=0, bucket_seconds=1, max_buckets=2)
        c = Compactor(cfg)
        # 5 distinct 1-second buckets
        ages = [(float(i), 1000 - i) for i in range(5)]
        h, now = _make_history("m", ages)
        c.compact("m", h, now)
        assert len(c.buckets_for("m")) <= 2

    def test_buckets_for_unknown_key_is_empty(self):
        c = Compactor()
        assert c.buckets_for("unknown") == []


# ---------------------------------------------------------------------------
# CompactorReporter
# ---------------------------------------------------------------------------

class TestCompactorReporter:
    def _make_result(self, key="pipe", removed=5, created=2):
        from pipewatch.compactor import CompactResult
        return CompactResult(key=key, buckets_created=created,
                             snapshots_removed=removed, buckets=[])

    def test_empty_results_message(self):
        r = CompactorReporter([])
        assert "no compaction" in r.format_text()

    def test_has_results_false_when_empty(self):
        assert not CompactorReporter([]).has_results()

    def test_has_results_true_when_populated(self):
        assert CompactorReporter([self._make_result()]).has_results()

    def test_total_removed(self):
        r = CompactorReporter([self._make_result(removed=3), self._make_result(removed=7)])
        assert r.total_removed() == 10

    def test_total_buckets(self):
        r = CompactorReporter([self._make_result(created=2), self._make_result(created=4)])
        assert r.total_buckets() == 6

    def test_format_text_contains_key(self):
        r = CompactorReporter([self._make_result(key="my_pipe")])
        assert "my_pipe" in r.format_text()

    def test_format_json_is_valid(self):
        import json
        r = CompactorReporter([self._make_result()])
        data = json.loads(r.format_json())
        assert "compactor" in data
        assert data["compactor"]["total_removed"] == 5
