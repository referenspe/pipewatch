"""Tests for pipewatch.pause."""
from datetime import datetime, timezone, timedelta

import pytest

from pipewatch.pause import PauseConfig, PauseController


def _now():
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestPauseConfig:
    def test_defaults(self):
        cfg = PauseConfig()
        assert cfg.max_pause_seconds == 3600
        assert cfg.auto_resume is True

    def test_from_dict_custom(self):
        cfg = PauseConfig.from_dict({"max_pause_seconds": 600, "auto_resume": False})
        assert cfg.max_pause_seconds == 600
        assert cfg.auto_resume is False

    def test_from_dict_defaults_when_missing(self):
        cfg = PauseConfig.from_dict({})
        assert cfg.max_pause_seconds == 3600

    def test_to_dict_round_trip(self):
        cfg = PauseConfig(max_pause_seconds=120, auto_resume=False)
        assert PauseConfig.from_dict(cfg.to_dict()).max_pause_seconds == 120


class TestPauseController:
    def test_pause_marks_key(self):
        ctrl = PauseController()
        result = ctrl.pause("pipe_a", now=_now())
        assert result.paused is True
        assert result.key == "pipe_a"

    def test_is_paused_true_after_pause(self):
        ctrl = PauseController()
        ctrl.pause("pipe_a", now=_now())
        assert ctrl.is_paused("pipe_a", now=_now()) is True

    def test_is_paused_false_before_pause(self):
        ctrl = PauseController()
        assert ctrl.is_paused("pipe_a", now=_now()) is False

    def test_resume_clears_key(self):
        ctrl = PauseController()
        ctrl.pause("pipe_a", now=_now())
        result = ctrl.resume("pipe_a", now=_now())
        assert result.paused is False
        assert ctrl.is_paused("pipe_a") is False

    def test_auto_resume_when_expired(self):
        ctrl = PauseController(PauseConfig(max_pause_seconds=60, auto_resume=True))
        ctrl.pause("pipe_a", now=_now())
        later = _now() + timedelta(seconds=120)
        result = ctrl.check("pipe_a", now=later)
        assert result.paused is False
        assert result.auto_resumed is True

    def test_no_auto_resume_when_disabled(self):
        ctrl = PauseController(PauseConfig(max_pause_seconds=60, auto_resume=False))
        ctrl.pause("pipe_a", now=_now())
        later = _now() + timedelta(seconds=120)
        result = ctrl.check("pipe_a", now=later)
        assert result.paused is True

    def test_paused_keys_lists_all(self):
        ctrl = PauseController()
        ctrl.pause("a", now=_now())
        ctrl.pause("b", now=_now())
        assert set(ctrl.paused_keys()) == {"a", "b"}

    def test_check_not_paused_key_returns_false(self):
        ctrl = PauseController()
        result = ctrl.check("unknown", now=_now())
        assert result.paused is False
