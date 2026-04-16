"""Tests for pipewatch.flush."""
import pytest
from pipewatch.flush import FlushConfig, FlushBuffer, FlushResult


class TestFlushConfig:
    def test_defaults(self):
        cfg = FlushConfig()
        assert cfg.max_buffer_size == 100
        assert cfg.flush_on_critical is True
        assert cfg.auto_flush_interval == 60.0

    def test_from_dict_custom(self):
        cfg = FlushConfig.from_dict({"max_buffer_size": 10, "flush_on_critical": False, "auto_flush_interval": 30.0})
        assert cfg.max_buffer_size == 10
        assert cfg.flush_on_critical is False
        assert cfg.auto_flush_interval == 30.0

    def test_from_dict_defaults_when_missing(self):
        cfg = FlushConfig.from_dict({})
        assert cfg.max_buffer_size == 100

    def test_to_dict_round_trip(self):
        cfg = FlushConfig(max_buffer_size=50, flush_on_critical=False, auto_flush_interval=15.0)
        assert FlushConfig.from_dict(cfg.to_dict()).max_buffer_size == 50


class TestFlushBuffer:
    def _buf(self, **kwargs):
        return FlushBuffer(config=FlushConfig(**kwargs))

    def test_push_no_flush_below_threshold(self):
        buf = self._buf(max_buffer_size=5, flush_on_critical=False)
        result = buf.push({"status": "ok"})
        assert result is None
        assert buf.size == 1

    def test_push_flushes_at_threshold(self):
        buf = self._buf(max_buffer_size=2, flush_on_critical=False)
        buf.push({"status": "ok"})
        result = buf.push({"status": "ok"})
        assert result is not None
        assert result.triggered_by == "threshold"
        assert result.flushed_count == 2
        assert buf.size == 0

    def test_push_flushes_on_critical(self):
        buf = self._buf(max_buffer_size=100, flush_on_critical=True)
        result = buf.push({"status": "critical"})
        assert result is not None
        assert result.triggered_by == "critical"

    def test_no_flush_on_critical_when_disabled(self):
        buf = self._buf(max_buffer_size=100, flush_on_critical=False)
        result = buf.push({"status": "critical"})
        assert result is None

    def test_manual_flush(self):
        buf = self._buf()
        buf.push({"status": "ok"})
        buf.push({"status": "warning"})
        result = buf.flush()
        assert result.flushed_count == 2
        assert result.triggered_by == "manual"
        assert buf.size == 0

    def test_drain_returns_items(self):
        buf = self._buf(flush_on_critical=False)
        buf.push({"status": "ok", "key": "a"})
        items = buf.drain()
        assert len(items) == 1
        assert items[0]["key"] == "a"
        assert buf.size == 0

    def test_flush_result_to_dict(self):
        r = FlushResult(flushed_count=3, remaining_count=0, triggered_by="interval")
        d = r.to_dict()
        assert d["flushed_count"] == 3
        assert d["triggered_by"] == "interval"
