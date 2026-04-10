"""Tests for pipewatch.config module."""
import json
import pytest
from pathlib import Path

from pipewatch.config import PipewatchConfig, TargetConfig
from pipewatch.metrics import MetricStatus


MINIMAL_TARGET = {
    "name": "queue_depth",
    "metric_key": "queue.depth",
    "threshold": {"warning": 100, "critical": 500, "comparison": "gt"},
}


class TestTargetConfig:
    def test_from_dict_sets_name(self):
        cfg = TargetConfig.from_dict(MINIMAL_TARGET)
        assert cfg.name == "queue_depth"

    def test_from_dict_sets_metric_key(self):
        cfg = TargetConfig.from_dict(MINIMAL_TARGET)
        assert cfg.metric_key == "queue.depth"

    def test_from_dict_default_interval(self):
        cfg = TargetConfig.from_dict(MINIMAL_TARGET)
        assert cfg.interval_seconds == 60.0

    def test_from_dict_custom_interval(self):
        data = {**MINIMAL_TARGET, "interval_seconds": 30.0}
        cfg = TargetConfig.from_dict(data)
        assert cfg.interval_seconds == 30.0

    def test_from_dict_tags_default_empty(self):
        cfg = TargetConfig.from_dict(MINIMAL_TARGET)
        assert cfg.tags == {}

    def test_from_dict_tags_populated(self):
        data = {**MINIMAL_TARGET, "tags": {"env": "prod"}}
        cfg = TargetConfig.from_dict(data)
        assert cfg.tags["env"] == "prod"

    def test_threshold_comparison_passed_through(self):
        cfg = TargetConfig.from_dict(MINIMAL_TARGET)
        assert cfg.threshold.comparison == "gt"


class TestPipewatchConfig:
    def test_from_dict_creates_targets(self):
        data = {"targets": [MINIMAL_TARGET]}
        cfg = PipewatchConfig.from_dict(data)
        assert len(cfg.targets) == 1

    def test_from_dict_default_log_level(self):
        cfg = PipewatchConfig.from_dict({})
        assert cfg.log_level == "INFO"

    def test_from_dict_custom_log_level(self):
        cfg = PipewatchConfig.from_dict({"log_level": "DEBUG"})
        assert cfg.log_level == "DEBUG"

    def test_from_dict_default_alert_channels(self):
        cfg = PipewatchConfig.from_dict({})
        assert "logging" in cfg.alert_channels

    def test_from_file_raises_when_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PipewatchConfig.from_file(tmp_path / "nonexistent.json")

    def test_from_file_loads_correctly(self, tmp_path):
        config_data = {"targets": [MINIMAL_TARGET], "log_level": "WARNING"}
        config_file = tmp_path / "pipewatch.json"
        config_file.write_text(json.dumps(config_data))
        cfg = PipewatchConfig.from_file(config_file)
        assert cfg.log_level == "WARNING"
        assert len(cfg.targets) == 1
