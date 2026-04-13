"""Tests for pipewatch.checkpoint_reporter."""
import json
import pytest
from pipewatch.checkpoint import CheckpointResult
from pipewatch.checkpoint_reporter import CheckpointReporter


def _make_result(
    stage: str = "etl",
    stalled: bool = False,
    regressed: bool = False,
    last_position: float = 0.0,
    current_position: float = 100.0,
    seconds_since_update: float = 5.0,
) -> CheckpointResult:
    return CheckpointResult(
        stage=stage,
        stalled=stalled,
        regressed=regressed,
        last_position=last_position,
        current_position=current_position,
        seconds_since_update=seconds_since_update,
    )


class TestCheckpointReporterText:
    def test_empty_results_message(self):
        r = CheckpointReporter([])
        assert "no results" in r.format_text().lower()

    def test_contains_stage_name(self):
        r = CheckpointReporter([_make_result(stage="load_stage")])
        assert "load_stage" in r.format_text()

    def test_ok_label_when_healthy(self):
        r = CheckpointReporter([_make_result()])
        assert "OK" in r.format_text()

    def test_stalled_label_when_stalled(self):
        r = CheckpointReporter([_make_result(stalled=True)])
        assert "STALLED" in r.format_text()

    def test_regressed_label_when_regressed(self):
        r = CheckpointReporter([_make_result(regressed=True)])
        assert "REGRESSED" in r.format_text()

    def test_has_stalls_true(self):
        r = CheckpointReporter([_make_result(stalled=True)])
        assert r.has_stalls()

    def test_has_stalls_false(self):
        r = CheckpointReporter([_make_result(stalled=False)])
        assert not r.has_stalls()

    def test_has_regressions_true(self):
        r = CheckpointReporter([_make_result(regressed=True)])
        assert r.has_regressions()

    def test_has_regressions_false(self):
        r = CheckpointReporter([_make_result(regressed=False)])
        assert not r.has_regressions()


class TestCheckpointReporterJson:
    def test_returns_valid_json(self):
        r = CheckpointReporter([_make_result()])
        parsed = json.loads(r.format_json())
        assert isinstance(parsed, list)

    def test_json_contains_stage(self):
        r = CheckpointReporter([_make_result(stage="transform")])
        parsed = json.loads(r.format_json())
        assert parsed[0]["stage"] == "transform"

    def test_json_contains_stalled_flag(self):
        r = CheckpointReporter([_make_result(stalled=True)])
        parsed = json.loads(r.format_json())
        assert parsed[0]["stalled"] is True

    def test_empty_list_returns_empty_json_array(self):
        r = CheckpointReporter([])
        assert json.loads(r.format_json()) == []
