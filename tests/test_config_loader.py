"""Tests for pipewatch.config_loader module."""
import json
import os
import pytest
from pathlib import Path

from pipewatch.config_loader import find_config_file, load_config
from pipewatch.config import PipewatchConfig


_SAMPLE = {
    "targets": [
        {
            "name": "lag",
            "metric_key": "consumer.lag",
            "threshold": {"warning": 50, "critical": 200, "comparison": "gt"},
        }
    ],
    "log_level": "DEBUG",
}


class TestFindConfigFile:
    def test_returns_none_when_absent(self, tmp_path):
        assert find_config_file(tmp_path) is None

    def test_finds_pipewatch_json(self, tmp_path):
        cfg_file = tmp_path / "pipewatch.json"
        cfg_file.write_text(json.dumps(_SAMPLE))
        found = find_config_file(tmp_path)
        assert found == cfg_file

    def test_finds_dotted_variant(self, tmp_path):
        cfg_file = tmp_path / ".pipewatch.json"
        cfg_file.write_text(json.dumps(_SAMPLE))
        found = find_config_file(tmp_path)
        assert found == cfg_file

    def test_prefers_non_dotted(self, tmp_path):
        (tmp_path / "pipewatch.json").write_text(json.dumps(_SAMPLE))
        (tmp_path / ".pipewatch.json").write_text(json.dumps(_SAMPLE))
        found = find_config_file(tmp_path)
        assert found.name == "pipewatch.json"


class TestLoadConfig:
    def test_explicit_path_loads_file(self, tmp_path):
        cfg_file = tmp_path / "custom.json"
        cfg_file.write_text(json.dumps(_SAMPLE))
        cfg = load_config(path=cfg_file)
        assert cfg.log_level == "DEBUG"

    def test_env_var_overrides_discovery(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "env_config.json"
        cfg_file.write_text(json.dumps({**_SAMPLE, "log_level": "WARNING"}))
        monkeypatch.setenv("PIPEWATCH_CONFIG", str(cfg_file))
        cfg = load_config(search_dir=tmp_path)
        assert cfg.log_level == "WARNING"

    def test_auto_discovery_fallback(self, tmp_path):
        cfg_file = tmp_path / "pipewatch.json"
        cfg_file.write_text(json.dumps(_SAMPLE))
        cfg = load_config(search_dir=tmp_path)
        assert len(cfg.targets) == 1

    def test_returns_default_when_nothing_found(self, tmp_path):
        cfg = load_config(search_dir=tmp_path)
        assert isinstance(cfg, PipewatchConfig)
        assert cfg.targets == []

    def test_explicit_path_takes_priority_over_env(self, tmp_path, monkeypatch):
        explicit = tmp_path / "explicit.json"
        explicit.write_text(json.dumps({**_SAMPLE, "log_level": "ERROR"}))
        env_file = tmp_path / "env.json"
        env_file.write_text(json.dumps({**_SAMPLE, "log_level": "DEBUG"}))
        monkeypatch.setenv("PIPEWATCH_CONFIG", str(env_file))
        cfg = load_config(path=explicit)
        assert cfg.log_level == "ERROR"
