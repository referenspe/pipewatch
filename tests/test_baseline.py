"""Tests for pipewatch.baseline."""
import json
import os
import tempfile

import pytest

from pipewatch.baseline import BaselineEntry, BaselineDeviation, BaselineStore
from pipewatch.metrics import MetricStatus, PipelineMetric
from pipewatch.metrics import ThresholdConfig


def _make_metric(key: str, value: float) -> PipelineMetric:
    thresholds = ThresholdConfig(warning=50.0, critical=90.0)
    return PipelineMetric(key=key, value=value, thresholds=thresholds, status=MetricStatus.OK)


# ---------------------------------------------------------------------------
class TestBaselineEntry:
    def test_to_dict_round_trip(self):
        entry = BaselineEntry(key="cpu", value=42.5, sample_count=3)
        restored = BaselineEntry.from_dict(entry.to_dict())
        assert restored.key == entry.key
        assert restored.value == entry.value
        assert restored.sample_count == entry.sample_count

    def test_from_dict_default_sample_count(self):
        entry = BaselineEntry.from_dict({"key": "mem", "value": 70.0})
        assert entry.sample_count == 1


# ---------------------------------------------------------------------------
class TestBaselineStore:
    def _store(self, tmp_path) -> BaselineStore:
        return BaselineStore(path=str(tmp_path / "baseline.json"))

    def test_get_returns_none_before_set(self, tmp_path):
        store = self._store(tmp_path)
        assert store.get("unknown") is None

    def test_set_and_get(self, tmp_path):
        store = self._store(tmp_path)
        metric = _make_metric("latency", 120.0)
        store.set(metric)
        entry = store.get("latency")
        assert entry is not None
        assert entry.value == 120.0

    def test_persists_to_disk(self, tmp_path):
        path = str(tmp_path / "baseline.json")
        store = BaselineStore(path=path)
        store.set(_make_metric("throughput", 500.0))
        # Re-load from disk
        store2 = BaselineStore(path=path)
        assert store2.get("throughput").value == 500.0

    def test_compare_returns_none_without_baseline(self, tmp_path):
        store = self._store(tmp_path)
        metric = _make_metric("cpu", 55.0)
        assert store.compare(metric) is None

    def test_compare_positive_deviation(self, tmp_path):
        store = self._store(tmp_path)
        store.set(_make_metric("cpu", 50.0))
        deviation = store.compare(_make_metric("cpu", 75.0))
        assert deviation is not None
        assert pytest.approx(deviation.deviation_pct, rel=1e-4) == 50.0

    def test_compare_negative_deviation(self, tmp_path):
        store = self._store(tmp_path)
        store.set(_make_metric("cpu", 100.0))
        deviation = store.compare(_make_metric("cpu", 80.0))
        assert pytest.approx(deviation.deviation_pct, rel=1e-4) == -20.0

    def test_compare_zero_baseline(self, tmp_path):
        store = self._store(tmp_path)
        store.set(_make_metric("errors", 0.0))
        deviation = store.compare(_make_metric("errors", 0.0))
        assert deviation.deviation_pct == 0.0

    def test_deviation_to_dict_keys(self, tmp_path):
        store = self._store(tmp_path)
        store.set(_make_metric("mem", 200.0))
        d = store.compare(_make_metric("mem", 250.0)).to_dict()
        assert set(d.keys()) == {"key", "baseline_value", "current_value", "deviation_pct"}

    def test_all_keys(self, tmp_path):
        store = self._store(tmp_path)
        store.set(_make_metric("a", 1.0))
        store.set(_make_metric("b", 2.0))
        assert sorted(store.all_keys()) == ["a", "b"]
