"""Tests for pipewatch metrics collection and threshold evaluation."""

import pytest
from datetime import datetime
from pipewatch.metrics import (
    MetricStatus,
    MetricsCollector,
    PipelineMetric,
    ThresholdConfig,
)


class TestThresholdConfig:
    def test_ok_when_below_warning(self):
        cfg = ThresholdConfig(warning=80.0, critical=95.0)
        assert cfg.evaluate(50.0) == MetricStatus.OK

    def test_warning_when_between_thresholds(self):
        cfg = ThresholdConfig(warning=80.0, critical=95.0)
        assert cfg.evaluate(85.0) == MetricStatus.WARNING

    def test_critical_when_above_critical(self):
        cfg = ThresholdConfig(warning=80.0, critical=95.0)
        assert cfg.evaluate(99.0) == MetricStatus.CRITICAL

    def test_lt_comparison_critical(self):
        cfg = ThresholdConfig(warning=20.0, critical=5.0, comparison="lt")
        assert cfg.evaluate(3.0) == MetricStatus.CRITICAL

    def test_lt_comparison_warning(self):
        cfg = ThresholdConfig(warning=20.0, critical=5.0, comparison="lt")
        assert cfg.evaluate(15.0) == MetricStatus.WARNING

    def test_no_thresholds_returns_ok(self):
        cfg = ThresholdConfig()
        assert cfg.evaluate(999.0) == MetricStatus.OK


class TestPipelineMetric:
    def test_to_dict_structure(self):
        metric = PipelineMetric(
            pipeline_name="etl_daily",
            metric_name="lag_seconds",
            value=42.5,
            unit="s",
            status=MetricStatus.WARNING,
            tags={"env": "prod"},
        )
        d = metric.to_dict()
        assert d["pipeline"] == "etl_daily"
        assert d["metric"] == "lag_seconds"
        assert d["value"] == 42.5
        assert d["unit"] == "s"
        assert d["status"] == "warning"
        assert d["tags"] == {"env": "prod"}
        assert "timestamp" in d


class TestMetricsCollector:
    def setup_method(self):
        self.collector = MetricsCollector()

    def test_record_without_threshold_returns_unknown(self):
        metric = self.collector.record("pipe_a", "row_count", 1000)
        assert metric.status == MetricStatus.UNKNOWN

    def test_record_with_threshold_evaluates_status(self):
        self.collector.register_threshold(
            "error_rate", ThresholdConfig(warning=5.0, critical=10.0)
        )
        metric = self.collector.record("pipe_a", "error_rate", 7.5, unit="%")
        assert metric.status == MetricStatus.WARNING
        assert metric.value == 7.5

    def test_latest_returns_most_recent(self):
        for i in range(10):
            self.collector.record("pipe_a", "throughput", float(i))
        latest = self.collector.latest(limit=3)
        assert len(latest) == 3
        assert latest[-1].value == 9.0

    def test_clear_removes_history(self):
        self.collector.record("pipe_a", "throughput", 100.0)
        self.collector.clear()
        assert self.collector.latest() == []

    def test_tags_are_stored(self):
        metric = self.collector.record("pipe_b", "lag", 30.0, tags={"region": "us-east"})
        assert metric.tags == {"region": "us-east"}
