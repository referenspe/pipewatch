"""Tests for pipewatch.staleness."""
from datetime import datetime, timedelta, timezone

import pytest

from pipewatch.history import MetricHistory
from pipewatch.metrics import MetricStatus, PipelineMetric, ThresholdConfig
from pipewatch.staleness import StalenessConfig, StalenessDetector


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_metric(key: str = "cpu") -> PipelineMetric:
    cfg = ThresholdConfig(warning=70.0, critical=90.0)
    return PipelineMetric(
        key=key,
        value=50.0,
        status=MetricStatus.OK,
        threshold=cfg,
    )


def _history_with_age(key: str, age_seconds: float) -> MetricHistory:
    """Return a MetricHistory whose latest snapshot is *age_seconds* old."""
    h = MetricHistory()
    metric = _make_metric(key)
    ts = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    h.record(metric, timestamp=ts)
    return h


# ---------------------------------------------------------------------------
# StalenessConfig
# ---------------------------------------------------------------------------

class TestStalenessConfig:
    def test_defaults(self):
        cfg = StalenessConfig()
        assert cfg.stale_after == 60
        assert cfg.critical_after == 300

    def test_raises_if_stale_not_positive(self):
        with pytest.raises(ValueError, match="stale_after must be positive"):
            StalenessConfig(stale_after=0, critical_after=300)

    def test_raises_if_critical_not_greater_than_stale(self):
        with pytest.raises(ValueError, match="critical_after must be greater"):
            StalenessConfig(stale_after=120, critical_after=60)

    def test_from_dict_custom(self):
        cfg = StalenessConfig.from_dict({"stale_after": 30, "critical_after": 120})
        assert cfg.stale_after == 30
        assert cfg.critical_after == 120

    def test_from_dict_defaults_when_missing(self):
        cfg = StalenessConfig.from_dict({})
        assert cfg.stale_after == 60
        assert cfg.critical_after == 300

    def test_to_dict_round_trip(self):
        cfg = StalenessConfig(stale_after=45, critical_after=180)
        assert StalenessConfig.from_dict(cfg.to_dict()).stale_after == 45


# ---------------------------------------------------------------------------
# StalenessDetector.check
# ---------------------------------------------------------------------------

class TestStalenessDetectorCheck:
    def _detector(self, stale=60, critical=300):
        return StalenessDetector(config=StalenessConfig(stale_after=stale,
                                                        critical_after=critical))

    def test_ok_when_fresh(self):
        h = _history_with_age("cpu", age_seconds=10)
        result = self._detector().check("cpu", h)
        assert not result.is_stale
        assert not result.is_critical

    def test_stale_when_between_thresholds(self):
        h = _history_with_age("cpu", age_seconds=120)
        result = self._detector().check("cpu", h)
        assert result.is_stale
        assert not result.is_critical

    def test_critical_when_beyond_critical_threshold(self):
        h = _history_with_age("cpu", age_seconds=400)
        result = self._detector().check("cpu", h)
        assert result.is_stale
        assert result.is_critical

    def test_no_history_is_critical(self):
        h = MetricHistory()
        result = self._detector().check("cpu", h)
        assert result.last_seen is None
        assert result.age_seconds is None
        assert result.is_critical

    def test_age_seconds_is_approximate(self):
        h = _history_with_age("mem", age_seconds=50)
        result = self._detector().check("mem", h)
        assert 49 <= result.age_seconds <= 51

    def test_to_dict_keys(self):
        h = _history_with_age("disk", age_seconds=10)
        result = self._detector().check("disk", h)
        d = result.to_dict()
        assert {"metric_key", "last_seen", "age_seconds",
                "is_stale", "is_critical"} <= d.keys()

    def test_check_all_returns_one_result_per_key(self):
        histories = {
            "cpu": _history_with_age("cpu", 10),
            "mem": _history_with_age("mem", 200),
        }
        results = self._detector().check_all(histories)
        assert len(results) == 2
        keys = {r.metric_key for r in results}
        assert keys == {"cpu", "mem"}
