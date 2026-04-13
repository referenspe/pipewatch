"""Tests for pipewatch.partition and pipewatch.partition_reporter."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import pytest

from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.partition import (
    PartitionAnalyser,
    PartitionConfig,
    PartitionGroup,
)
from pipewatch.partition_reporter import PartitionReporter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str, value: float, status: MetricStatus) -> PipelineMetric:
    cfg = ThresholdConfig(warning=50.0, critical=90.0)
    return PipelineMetric(key=key, value=value, status=status, threshold=cfg)


# ---------------------------------------------------------------------------
# PartitionConfig
# ---------------------------------------------------------------------------

class TestPartitionConfig:
    def test_defaults(self):
        cfg = PartitionConfig()
        assert cfg.key_field == "partition"
        assert cfg.max_partitions == 64

    def test_from_dict_custom(self):
        cfg = PartitionConfig.from_dict({"key_field": "region", "max_partitions": 10})
        assert cfg.key_field == "region"
        assert cfg.max_partitions == 10

    def test_from_dict_defaults_when_missing(self):
        cfg = PartitionConfig.from_dict({})
        assert cfg.max_partitions == 64

    def test_to_dict_round_trip(self):
        cfg = PartitionConfig(key_field="shard", max_partitions=8)
        assert PartitionConfig.from_dict(cfg.to_dict()).max_partitions == 8


# ---------------------------------------------------------------------------
# PartitionAnalyser
# ---------------------------------------------------------------------------

class TestPartitionAnalyser:
    def test_empty_metrics_returns_empty_result(self):
        analyser = PartitionAnalyser()
        result = analyser.analyse([], {})
        assert result.groups == {}
        assert not result.truncated

    def test_groups_by_partition_label(self):
        m1 = _make_metric("cpu", 20.0, MetricStatus.OK)
        m2 = _make_metric("mem", 80.0, MetricStatus.WARNING)
        m3 = _make_metric("disk", 95.0, MetricStatus.CRITICAL)
        pv = {"cpu": "us-east", "mem": "us-east", "disk": "eu-west"}
        result = PartitionAnalyser().analyse([m1, m2, m3], pv)
        assert set(result.groups.keys()) == {"us-east", "eu-west"}
        assert result.groups["us-east"].count == 2
        assert result.groups["eu-west"].count == 1

    def test_worst_status_propagates(self):
        m1 = _make_metric("a", 10.0, MetricStatus.OK)
        m2 = _make_metric("b", 95.0, MetricStatus.CRITICAL)
        result = PartitionAnalyser().analyse([m1, m2], {"a": "p1", "b": "p1"})
        assert result.groups["p1"].worst_status == MetricStatus.CRITICAL

    def test_truncation_when_max_partitions_exceeded(self):
        cfg = PartitionConfig(max_partitions=2)
        metrics = [_make_metric(f"k{i}", float(i), MetricStatus.OK) for i in range(6)]
        pv = {f"k{i}": f"part{i}" for i in range(6)}
        result = PartitionAnalyser(cfg).analyse(metrics, pv)
        assert len(result.groups) == 2
        assert result.truncated

    def test_default_partition_for_unmapped_metric(self):
        m = _make_metric("x", 1.0, MetricStatus.OK)
        result = PartitionAnalyser().analyse([m], {})
        assert "__default__" in result.groups


# ---------------------------------------------------------------------------
# PartitionReporter
# ---------------------------------------------------------------------------

class TestPartitionReporter:
    def _result_with_critical(self):
        m = _make_metric("z", 99.0, MetricStatus.CRITICAL)
        return PartitionAnalyser().analyse([m], {"z": "shard-1"})

    def test_empty_groups_message(self):
        from pipewatch.partition import PartitionResult
        reporter = PartitionReporter()
        text = reporter.format_text(PartitionResult())
        assert "no partitions" in text

    def test_format_text_contains_partition_key(self):
        result = self._result_with_critical()
        text = PartitionReporter().format_text(result)
        assert "shard-1" in text

    def test_format_text_contains_status(self):
        result = self._result_with_critical()
        text = PartitionReporter().format_text(result)
        assert "CRITICAL" in text

    def test_has_critical_true(self):
        result = self._result_with_critical()
        assert PartitionReporter().has_critical(result)

    def test_has_warnings_false_when_only_critical(self):
        result = self._result_with_critical()
        assert not PartitionReporter().has_warnings(result)

    def test_format_json_valid(self):
        result = self._result_with_critical()
        payload = json.loads(PartitionReporter(title="T").format_json(result))
        assert payload["title"] == "T"
        assert "groups" in payload["result"]

    def test_truncated_flag_in_text(self):
        cfg = PartitionConfig(max_partitions=1)
        metrics = [_make_metric(f"k{i}", float(i), MetricStatus.OK) for i in range(3)]
        pv = {f"k{i}": f"p{i}" for i in range(3)}
        result = PartitionAnalyser(cfg).analyse(metrics, pv)
        text = PartitionReporter().format_text(result)
        assert "truncated" in text
