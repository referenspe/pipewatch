"""Tests for pipewatch.tee."""
import pytest

from pipewatch.tee import Tee, TeeConfig, TeeResult


# ---------------------------------------------------------------------------
# TeeConfig
# ---------------------------------------------------------------------------

class TestTeeConfig:
    def test_defaults(self):
        cfg = TeeConfig()
        assert cfg.sinks == []
        assert cfg.drop_on_error is False
        assert cfg.max_sinks == 8

    def test_from_dict_custom(self):
        cfg = TeeConfig.from_dict(
            {"sinks": ["s3", "kafka"], "drop_on_error": True, "max_sinks": 4}
        )
        assert cfg.sinks == ["s3", "kafka"]
        assert cfg.drop_on_error is True
        assert cfg.max_sinks == 4

    def test_from_dict_defaults_when_missing(self):
        cfg = TeeConfig.from_dict({})
        assert cfg.sinks == []
        assert cfg.drop_on_error is False
        assert cfg.max_sinks == 8

    def test_to_dict_round_trip(self):
        original = TeeConfig(sinks=["a", "b"], drop_on_error=True, max_sinks=5)
        assert TeeConfig.from_dict(original.to_dict()).to_dict() == original.to_dict()

    def test_raises_if_max_sinks_less_than_one(self):
        with pytest.raises(ValueError, match="max_sinks"):
            TeeConfig(max_sinks=0)

    def test_raises_if_sinks_exceed_max(self):
        with pytest.raises(ValueError, match="exceeds max_sinks"):
            TeeConfig(sinks=["a", "b", "c"], max_sinks=2)


# ---------------------------------------------------------------------------
# Tee.distribute
# ---------------------------------------------------------------------------

def _make_tee(sinks, drop_on_error=False):
    cfg = TeeConfig(sinks=sinks, drop_on_error=drop_on_error)
    return Tee(cfg)


class TestTeeDistribute:
    def test_sends_to_all_present_sinks(self):
        received = {}

        def handler(key, payload, name=None):
            received[name] = (key, payload)

        tee = _make_tee(["a", "b"])
        sink_map = {
            "a": lambda k, p: received.__setitem__("a", (k, p)),
            "b": lambda k, p: received.__setitem__("b", (k, p)),
        }
        result = tee.distribute("cpu", {"v": 1}, sink_map)
        assert result.success_count == 2
        assert result.failure_count == 0
        assert result.all_succeeded is True
        assert "a" in received and "b" in received

    def test_missing_sink_recorded_as_failed(self):
        tee = _make_tee(["present", "missing"])
        sink_map = {"present": lambda k, p: None}
        result = tee.distribute("mem", {}, sink_map)
        assert "missing" in result.failed
        assert "present" in result.sent_to

    def test_error_recorded_when_drop_on_error_true(self):
        def bad_handler(k, p):
            raise RuntimeError("boom")

        tee = _make_tee(["bad"], drop_on_error=True)
        result = tee.distribute("disk", {}, {"bad": bad_handler})
        assert result.failure_count == 1
        assert result.all_succeeded is False

    def test_error_propagates_when_drop_on_error_false(self):
        def bad_handler(k, p):
            raise RuntimeError("boom")

        tee = _make_tee(["bad"], drop_on_error=False)
        with pytest.raises(RuntimeError, match="boom"):
            tee.distribute("disk", {}, {"bad": bad_handler})

    def test_to_dict_contains_expected_keys(self):
        tee = _make_tee(["x"])
        result = tee.distribute("k", {}, {"x": lambda a, b: None})
        d = result.to_dict()
        assert "metric_key" in d
        assert "sent_to" in d
        assert "failed" in d
        assert "success_count" in d
        assert "failure_count" in d
        assert "all_succeeded" in d
