"""Tests for pipewatch.snapshot_reporter."""
from pipewatch.snapshot import SnapshotConfig, SnapshotCapture
from pipewatch.snapshot_reporter import SnapshotReporter
from pipewatch.metrics import PipelineMetric, MetricStatus, ThresholdConfig


def _make_metric(key: str, value: float, status: MetricStatus) -> PipelineMetric:
    t = ThresholdConfig(warning=50.0, critical=90.0)
    m = PipelineMetric(key=key, value=value, threshold=t)
    object.__setattr__(m, "status", status)
    return m


def _make_result(include_ok=True, metrics=None):
    if metrics is None:
        metrics = [
            _make_metric("cpu", 20.0, MetricStatus.OK),
            _make_metric("mem", 75.0, MetricStatus.WARNING),
            _make_metric("disk", 95.0, MetricStatus.CRITICAL),
        ]
    cap = SnapshotCapture(SnapshotConfig(include_ok=include_ok))
    return cap.capture(metrics)


class TestSnapshotReporterText:
    def test_empty_entries_message(self):
        cap = SnapshotCapture()
        result = cap.capture([])
        r = SnapshotReporter(result)
        assert "No entries" in r.format_text()

    def test_has_entries_false_when_empty(self):
        cap = SnapshotCapture()
        assert not SnapshotReporter(cap.capture([])).has_entries()

    def test_has_entries_true_when_populated(self):
        assert SnapshotReporter(_make_result()).has_entries()

    def test_has_critical_true(self):
        assert SnapshotReporter(_make_result()).has_critical()

    def test_has_critical_false_when_only_ok(self):
        result = _make_result(metrics=[_make_metric("x", 1.0, MetricStatus.OK)])
        assert not SnapshotReporter(result).has_critical()

    def test_has_warnings_true(self):
        assert SnapshotReporter(_make_result()).has_warnings()

    def test_contains_metric_key(self):
        text = SnapshotReporter(_make_result()).format_text()
        assert "mem" in text

    def test_contains_status_label(self):
        text = SnapshotReporter(_make_result()).format_text()
        assert "CRITICAL" in text or "WARNING" in text

    def test_format_json_valid(self):
        import json
        j = SnapshotReporter(_make_result()).format_json()
        parsed = json.loads(j)
        assert "entries" in parsed
