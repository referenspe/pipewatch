"""Tests for pipewatch.snapshot."""
import pytest
from datetime import datetime, timezone
from pipewatch.snapshot import SnapshotConfig, SnapshotCapture, SnapshotEntry
from pipewatch.metrics import PipelineMetric, MetricStatus, ThresholdConfig


def _make_metric(key: str, value: float, status: MetricStatus) -> PipelineMetric:
    t = ThresholdConfig(warning=50.0, critical=90.0)
    m = PipelineMetric(key=key, value=value, threshold=t)
    m._status = status  # type: ignore[attr-defined]
    object.__setattr__(m, "status", status)
    return m


class TestSnapshotConfig:
    def test_defaults(self):
        c = SnapshotConfig()
        assert c.label == "default"
        assert c.include_ok is True
        assert c.max_entries == 500

    def test_from_dict_custom(self):
        c = SnapshotConfig.from_dict({"label": "prod", "include_ok": False, "max_entries": 10})
        assert c.label == "prod"
        assert c.include_ok is False
        assert c.max_entries == 10

    def test_from_dict_defaults_when_missing(self):
        c = SnapshotConfig.from_dict({})
        assert c.label == "default"
        assert c.include_ok is True

    def test_to_dict_round_trip(self):
        c = SnapshotConfig(label="staging", include_ok=False, max_entries=100)
        assert SnapshotConfig.from_dict(c.to_dict()).label == "staging"


class TestSnapshotCapture:
    def _metrics(self):
        return [
            _make_metric("cpu", 20.0, MetricStatus.OK),
            _make_metric("mem", 75.0, MetricStatus.WARNING),
            _make_metric("disk", 95.0, MetricStatus.CRITICAL),
        ]

    def test_captures_all_by_default(self):
        cap = SnapshotCapture()
        result = cap.capture(self._metrics())
        assert len(result.entries) == 3

    def test_excludes_ok_when_configured(self):
        cap = SnapshotCapture(SnapshotConfig(include_ok=False))
        result = cap.capture(self._metrics())
        keys = [e.metric_key for e in result.entries]
        assert "cpu" not in keys
        assert "mem" in keys

    def test_respects_max_entries(self):
        cap = SnapshotCapture(SnapshotConfig(max_entries=2))
        result = cap.capture(self._metrics())
        assert len(result.entries) == 2

    def test_label_propagated(self):
        cap = SnapshotCapture(SnapshotConfig(label="test-run"))
        result = cap.capture([])
        assert result.label == "test-run"

    def test_entry_values_correct(self):
        cap = SnapshotCapture()
        result = cap.capture([_make_metric("latency", 42.5, MetricStatus.OK)])
        assert result.entries[0].value == pytest.approx(42.5)

    def test_to_dict_contains_entries(self):
        cap = SnapshotCapture()
        result = cap.capture(self._metrics())
        d = result.to_dict()
        assert "entries" in d
        assert len(d["entries"]) == 3

    def test_to_json_is_valid(self):
        import json
        cap = SnapshotCapture()
        result = cap.capture(self._metrics())
        parsed = json.loads(result.to_json())
        assert parsed["label"] == "default"
