"""Tests for pipewatch.backpressure."""
import pytest
from pipewatch.backpressure import BackpressureConfig, BackpressureDetector


# ---------------------------------------------------------------------------
# BackpressureConfig
# ---------------------------------------------------------------------------
class TestBackpressureConfig:
    def test_defaults(self):
        cfg = BackpressureConfig()
        assert cfg.warn_lag == 10.0
        assert cfg.critical_lag == 30.0
        assert cfg.window == 5

    def test_from_dict_custom(self):
        cfg = BackpressureConfig.from_dict(
            {"warn_lag": 5.0, "critical_lag": 15.0, "window": 3}
        )
        assert cfg.warn_lag == 5.0
        assert cfg.critical_lag == 15.0
        assert cfg.window == 3

    def test_from_dict_defaults_when_missing(self):
        cfg = BackpressureConfig.from_dict({})
        assert cfg.warn_lag == 10.0

    def test_to_dict_round_trip(self):
        cfg = BackpressureConfig(warn_lag=7.0, critical_lag=20.0, window=4)
        assert BackpressureConfig.from_dict(cfg.to_dict()).warn_lag == 7.0

    def test_raises_if_warn_lag_not_positive(self):
        with pytest.raises(ValueError, match="warn_lag"):
            BackpressureConfig(warn_lag=0)

    def test_raises_if_critical_not_greater_than_warn(self):
        with pytest.raises(ValueError, match="critical_lag"):
            BackpressureConfig(warn_lag=20.0, critical_lag=20.0)

    def test_raises_if_window_less_than_one(self):
        with pytest.raises(ValueError, match="window"):
            BackpressureConfig(window=0)


# ---------------------------------------------------------------------------
# BackpressureDetector
# ---------------------------------------------------------------------------
def _detector(warn=10.0, critical=30.0, window=5):
    return BackpressureDetector(
        config=BackpressureConfig(warn_lag=warn, critical_lag=critical, window=window)
    )


class TestBackpressureDetector:
    def test_evaluate_returns_none_for_unknown_stage(self):
        d = _detector()
        assert d.evaluate("unknown") is None

    def test_ok_when_avg_below_warn(self):
        d = _detector()
        for _ in range(3):
            d.record("stage_a", 5.0)
        result = d.evaluate("stage_a")
        assert result is not None
        assert result.level == "ok"

    def test_warning_when_avg_between_thresholds(self):
        d = _detector()
        for _ in range(3):
            d.record("stage_b", 15.0)
        result = d.evaluate("stage_b")
        assert result.level == "warning"

    def test_critical_when_avg_above_critical(self):
        d = _detector()
        for _ in range(3):
            d.record("stage_c", 50.0)
        result = d.evaluate("stage_c")
        assert result.level == "critical"

    def test_window_limits_sample_count(self):
        d = _detector(window=3)
        for i in range(10):
            d.record("s", float(i))
        result = d.evaluate("s")
        assert result.sample_count == 3

    def test_avg_lag_is_correct(self):
        d = _detector(window=4)
        for v in [2.0, 4.0, 6.0, 8.0]:
            d.record("s", v)
        result = d.evaluate("s")
        assert result.avg_lag == pytest.approx(5.0)

    def test_evaluate_all_covers_all_stages(self):
        d = _detector()
        d.record("alpha", 1.0)
        d.record("beta", 1.0)
        results = d.evaluate_all()
        stages = {r.stage for r in results}
        assert stages == {"alpha", "beta"}

    def test_to_dict_contains_expected_keys(self):
        d = _detector()
        d.record("x", 5.0)
        data = d.evaluate("x").to_dict()
        assert set(data.keys()) == {"stage", "avg_lag", "level", "sample_count"}
