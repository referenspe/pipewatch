"""Tests for pipewatch.retention."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pipewatch.history import MetricHistory, MetricSnapshot
from pipewatch.retention import RetentionManager, RetentionPolicy


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _snapshot(key: str, value: float, age_seconds: float = 0.0) -> MetricSnapshot:
    ts = datetime.now(tz=timezone.utc) - timedelta(seconds=age_seconds)
    return MetricSnapshot(key=key, value=value, status="ok", recorded_at=ts)


def _history_with(*snapshots: MetricSnapshot) -> MetricHistory:
    h = MetricHistory()
    for s in snapshots:
        h.replace(s.key, list(h.all(s.key)) + [s])
    return h


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------

class TestRetentionPolicy:
    def test_defaults(self):
        p = RetentionPolicy()
        assert p.max_age_seconds == 3600.0
        assert p.max_entries == 1000

    def test_from_dict(self):
        p = RetentionPolicy.from_dict({"max_age_seconds": 60, "max_entries": 5})
        assert p.max_age_seconds == 60.0
        assert p.max_entries == 5

    def test_to_dict_round_trip(self):
        p = RetentionPolicy(max_age_seconds=120.0, max_entries=50)
        assert RetentionPolicy.from_dict(p.to_dict()) == p

    def test_raises_on_non_positive_age(self):
        with pytest.raises(ValueError, match="max_age_seconds"):
            RetentionPolicy(max_age_seconds=0)

    def test_raises_on_zero_max_entries(self):
        with pytest.raises(ValueError, match="max_entries"):
            RetentionPolicy(max_entries=0)


# ---------------------------------------------------------------------------
# RetentionManager.prune
# ---------------------------------------------------------------------------

class TestRetentionManagerPrune:
    def test_removes_expired_snapshots(self):
        policy = RetentionPolicy(max_age_seconds=30.0, max_entries=100)
        mgr = RetentionManager(policy)

        h = MetricHistory()
        h.replace("cpu", [
            _snapshot("cpu", 10.0, age_seconds=60),  # old
            _snapshot("cpu", 20.0, age_seconds=10),  # fresh
        ])

        result = mgr.prune("cpu", h)
        assert result.removed_count == 1
        assert result.remaining_count == 1
        assert list(h.all("cpu"))[0].value == 20.0

    def test_enforces_max_entries(self):
        policy = RetentionPolicy(max_age_seconds=3600.0, max_entries=3)
        mgr = RetentionManager(policy)

        h = MetricHistory()
        h.replace("mem", [_snapshot("mem", float(i)) for i in range(10)])

        result = mgr.prune("mem", h)
        assert result.remaining_count == 3
        assert result.removed_count == 7
        # most recent kept
        values = [s.value for s in h.all("mem")]
        assert values == [7.0, 8.0, 9.0]

    def test_no_removal_when_within_policy(self):
        policy = RetentionPolicy(max_age_seconds=3600.0, max_entries=100)
        mgr = RetentionManager(policy)

        h = MetricHistory()
        h.replace("disk", [_snapshot("disk", 1.0, age_seconds=5)])

        result = mgr.prune("disk", h)
        assert result.removed_count == 0
        assert result.remaining_count == 1

    def test_result_contains_metric_key(self):
        policy = RetentionPolicy(max_age_seconds=3600.0, max_entries=100)
        mgr = RetentionManager(policy)
        h = MetricHistory()
        result = mgr.prune("latency", h)
        assert result.metric_key == "latency"


# ---------------------------------------------------------------------------
# RetentionManager.prune_all
# ---------------------------------------------------------------------------

class TestRetentionManagerPruneAll:
    def test_returns_result_per_key(self):
        policy = RetentionPolicy(max_age_seconds=3600.0, max_entries=100)
        mgr = RetentionManager(policy)

        histories = {
            "cpu": MetricHistory(),
            "mem": MetricHistory(),
        }
        results = mgr.prune_all(histories)
        assert len(results) == 2
        keys = {r.metric_key for r in results}
        assert keys == {"cpu", "mem"}
