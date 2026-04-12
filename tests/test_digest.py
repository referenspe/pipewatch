"""Tests for pipewatch.digest."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pipewatch.digest import Digest, DigestBuilder, DigestConfig, DigestEntry
from pipewatch.metrics import MetricStatus


def _make_summary(mean: float = 1.0, count: int = 5):
    s = MagicMock()
    s.mean = mean
    s.count = count
    s.to_dict.return_value = {"mean": mean, "count": count}
    return s


_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestDigestConfig:
    def test_defaults(self):
        cfg = DigestConfig()
        assert cfg.title == "Pipeline Health Digest"
        assert cfg.include_ok is False
        assert cfg.max_entries == 50

    def test_from_dict_custom(self):
        cfg = DigestConfig.from_dict({"title": "My Digest", "include_ok": True, "max_entries": 10})
        assert cfg.title == "My Digest"
        assert cfg.include_ok is True
        assert cfg.max_entries == 10

    def test_from_dict_defaults_when_missing(self):
        cfg = DigestConfig.from_dict({})
        assert cfg.max_entries == 50

    def test_to_dict_round_trip(self):
        cfg = DigestConfig(title="T", include_ok=True, max_entries=5)
        assert DigestConfig.from_dict(cfg.to_dict()).max_entries == 5


class TestDigest:
    def _build(self, statuses):
        entries = [
            DigestEntry(metric_key=k, status=s, summary=_make_summary())
            for k, s in statuses.items()
        ]
        return Digest(title="Test", generated_at=_NOW, entries=entries)

    def test_critical_count(self):
        d = self._build({"a": MetricStatus.CRITICAL, "b": MetricStatus.OK})
        assert d.critical_count == 1

    def test_warning_count(self):
        d = self._build({"a": MetricStatus.WARNING, "b": MetricStatus.WARNING})
        assert d.warning_count == 2

    def test_ok_count(self):
        d = self._build({"a": MetricStatus.OK})
        assert d.ok_count == 1

    def test_overall_critical_when_any_critical(self):
        d = self._build({"a": MetricStatus.CRITICAL, "b": MetricStatus.WARNING})
        assert d.overall_status == MetricStatus.CRITICAL

    def test_overall_warning_when_no_critical(self):
        d = self._build({"a": MetricStatus.WARNING, "b": MetricStatus.OK})
        assert d.overall_status == MetricStatus.WARNING

    def test_overall_ok_when_all_ok(self):
        d = self._build({"a": MetricStatus.OK})
        assert d.overall_status == MetricStatus.OK

    def test_to_dict_contains_overall_status(self):
        d = self._build({"a": MetricStatus.CRITICAL})
        assert d.to_dict()["overall_status"] == "critical"


class TestDigestBuilder:
    def test_excludes_ok_by_default(self):
        builder = DigestBuilder()
        summaries = {"m1": _make_summary()}
        statuses = {"m1": MetricStatus.OK}
        digest = builder.build(summaries, statuses, now=_NOW)
        assert len(digest.entries) == 0

    def test_includes_ok_when_configured(self):
        builder = DigestBuilder(DigestConfig(include_ok=True))
        summaries = {"m1": _make_summary()}
        statuses = {"m1": MetricStatus.OK}
        digest = builder.build(summaries, statuses, now=_NOW)
        assert len(digest.entries) == 1

    def test_respects_max_entries(self):
        builder = DigestBuilder(DigestConfig(include_ok=True, max_entries=2))
        summaries = {f"m{i}": _make_summary() for i in range(5)}
        statuses = {k: MetricStatus.OK for k in summaries}
        digest = builder.build(summaries, statuses, now=_NOW)
        assert len(digest.entries) == 2

    def test_critical_entries_sorted_first(self):
        builder = DigestBuilder(DigestConfig(include_ok=True))
        summaries = {"ok": _make_summary(), "crit": _make_summary()}
        statuses = {"ok": MetricStatus.OK, "crit": MetricStatus.CRITICAL}
        digest = builder.build(summaries, statuses, now=_NOW)
        assert digest.entries[0].status == MetricStatus.CRITICAL

    def test_uses_provided_now(self):
        builder = DigestBuilder(DigestConfig(include_ok=True))
        digest = builder.build({"m": _make_summary()}, {"m": MetricStatus.OK}, now=_NOW)
        assert digest.generated_at == _NOW
